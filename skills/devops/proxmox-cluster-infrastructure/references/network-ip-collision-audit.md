# Network IP-collision audit against the physical asset inventory

Session-verified procedure (2026-09-09, MARION lab) for proving that statically assigned
guest IPs don't collide with physical devices or the DHCP pool. Run this whenever a build
has assigned statics on a shared LAN, or the user asks to "double-check you haven't created
network problems."

## Inputs

1. **Known-device asset sheet** (xlsx: hostnames, IPs, MACs). Parse with stdlib only —
   no openpyxl needed:
   ```python
   import zipfile
   from xml.etree import ElementTree as ET
   z = zipfile.ZipFile(path)
   ss = [''.join(t.text or '' for t in si.iter('{…main}t'))
         for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
   for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).iter('{…main}row'):
       # cell values: t='s' → shared[int(v)], else v.text; None → ''
   ```
   Iterate `xl/worksheets/sheetN.xml` in a try/except — sheet count varies.
2. **Your assigned statics** (from Proxmox configs, not from memory).

## Procedure

1. **Populate ARP**: ping-sweep the /24 (`ping -c1 -W1 <ip>` in a loop, ignore results),
   then `ip neigh show`. Hosts that block ICMP still appear if they answered ARP or
   replied earlier.
2. **MAC classification discriminator** (fast, reliable here):
   - `bc:24:11:*` = Proxmox/KVM guest vNIC (QEMU).
   - Anything else = physical device (Dell `20:88:10:*`, Gigabyte `d8:5e:d3:*`,
     Minisforum `38:05:25:*`, PDU `00:06:67:*`, switch `78:D8:00:*`/`1C:2A:A3:*`, etc.).
   If a KNOWN-DEVICE IP answers with a `bc:24:11:*` MAC → a guest has stolen it.
   If one of YOUR guest IPs answers with a vendor MAC → wrong machine owns it (the
   corosync-ring collision signature: port REFUSED while the service is confirmed
   listening on the CT).
3. **Verify your guests' real MACs** (`pct exec <ct> -- ip link show eth0` /
   `qm guest cmd <vmid> network-get-interfaces`) and require ARP-for-<ip> == guest MAC.
4. **Proxmox-level addressing check**: `qm config <vmid> | grep ^ipconfig` and
   `pct config <ct> | grep net0` — confirm static `ip=/24,gw=` at the hypervisor level,
   i.e. no DHCP dependence for infrastructure roles.
5. **DHCP pool boundary check** (the silent-collision risk): statics must sit OUTSIDE
   every DHCP pool, or the firewall can hand your static IP to someone else later.
   Extract pools from OPNsense `config.xml` (flow below) — grep `<range><from>/<to>`.
   MARION fact: VLAN20 pool = 10.0.20.190–.250, VLAN10 pool = 10.0.10.190–.250; statics
   below .190 are safe.
6. **DHCP-leased infrastructure guests**: if an infra guest leases an address INSIDE the
   pool (e.g. CT906 @ .195), flag it and recommend a `<staticmap>` pin on the firewall
   (needs MAC + desired IP). Lease is legitimate, but unpinned = migratable.
7. **Never conclude from ping alone.** ICMP can be filtered per host (observed: ping
   FAIL but TCP :5432 OPEN on the same IP). Test the actual service port:
   `timeout 3 bash -c 'cat < /dev/null > /dev/tcp/<ip>/<port>'`.

## OPNsense config.xml download (session-logged UI flow)

Extends the unbound auth chain in `opnsense-unbound-dns.md`:

1. UI login as in the unbound reference: GET `/index.php`, parse hidden fields with
   `re.findall(r'name="([^"]+)" value="([^"]*)" autocomplete', page)` (field NAME is
   randomized), POST `usernamefld=root&passwordfld=<pw>&login=1` + hidden fields.
2. Confirm login: `curl -b jar -L /index.php` → body contains "Dashboard".
3. GET `/diag_backup.php`, find the NEW randomized hidden field (same regex).
4. POST `{csrf_field}={csrf_val}&download=Download+configuration` → response body IS
   config.xml (~1.6 MB).
5. **Security**: config.xml contains private keys, password hashes, certs. Process in
   memory only — never write to disk, never print secrets; grep only the sections needed
   (dhcpd ranges, staticmap).

## Report shape that worked

Table: IP | device | status (✓ MAC matches sheet / ✓ clean guest / ⚠ DHCP-in-pool),
plus "repairs made during audit" section (config repoints discovered while verifying),
plus durable facts saved to memory (pool boundaries, forbidden IPs like the corosync
node address).
