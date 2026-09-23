#!/usr/bin/env python3
"""MARION fleet probe — read-only.

Answers, without touching any service:
  * which public model names LLM Manager exposes
  * for each alias: is it LOCAL (vllm/llama.cpp, with system_fingerprint) or CLOUD (provider router)?
  * the alias -> backend-node map
  * per-node live ExecStart + GPU inventory (via PVE guest-exec)

Usage:
    python3 fleet_probe.py                 # aliases + routing map
    python3 fleet_probe.py --nodes         # also dump per-VM ExecStart/GPU (needs pve.py)

Reads the agent key from the Hermes profile .env (never echoed, never printed).
"""
import argparse, json, os, re, ssl, subprocess, sys, urllib.request

PROFILE_ENV = os.path.expanduser(
    "~/.hermes/profiles/agent_stea004_entrepreneur/.env")
BASE = "https://llm-manager.marion-ia-usa.internal"
PVE_DIR = os.path.expanduser("~/.llm-manager-v011")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

NODES = {  # ip -> (proxmox node, vmid)
    "10.0.20.161": ("miam00111", 103),
    "10.0.20.162": ("miam00112", 401),
    "10.0.20.163": ("miam00143", 109),
    "10.0.20.164": ("miam00144", 111),
    "10.0.20.165": ("miam-00149", 149),
}


def agent_key():
    txt = open(PROFILE_ENV).read()
    m = re.search(r"^MARION_LOCAL_API_KEY=(.*)$", txt, re.M)
    if not m:
        sys.exit("MARION_LOCAL_API_KEY not found in profile .env")
    return m.group(1).strip().strip("'\"")


def _post(path, key, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, context=CTX, timeout=60))


def routing_map(key):
    models = json.load(urllib.request.urlopen(
        urllib.request.Request(BASE + "/v1/models",
                               headers={"Authorization": f"Bearer {key}"}),
        context=CTX, timeout=30))["data"]
    names = [m["id"] for m in models]
    print(f"### /v1/models ({len(names)}): {', '.join(names)}\n")

    print("### alias -> backend")
    local, cloud = {}, {}
    for name in names:
        try:
            d = _post("/v1/chat/completions", key,
                      {"model": name,
                       "messages": [{"role": "user", "content": "hi"}],
                       "max_tokens": 1})
            fp = d.get("system_fingerprint")
            prov = d.get("provider")
            rid = str(d.get("id", ""))
            if prov or rid.startswith("gen-"):
                kind = f"CLOUD   provider={prov} id={rid[:18]}"
                cloud[name] = prov
            else:
                kind = f"LOCAL   fp={fp}"
                local.setdefault(fp, []).append(name)
            print(f"  {name:26} {kind}")
        except Exception as exc:                       # noqa: BLE001
            print(f"  {name:26} FAIL {str(exc)[:70]}")
    print("\n### fingerprint -> aliases (group by node)")
    for fp, aliases in local.items():
        print(f"  {fp:38} {', '.join(aliases)}")
    if cloud:
        print("\n### CLOUD aliases (no local deployment behind them)")
        for name, prov in cloud.items():
            print(f"  {name:26} {prov}")
    return local


def node_fingerprints():
    """Probe each GPU VM directly with its OWN served model name.

    PITFALL: hitting :8000/v1/chat/completions with a made-up model name returns
    HTTP 404 — you must pass that server's --served-model-name.
    """
    served = {"10.0.20.161": "qwen3.8-27b", "10.0.20.162": "qwen3.6-35b-a3b",
              "10.0.20.163": "qwen3.6-35b-a3b", "10.0.20.164": "qwen3.6-35b-a3b"}
    print("\n### node -> fingerprint (direct :8000)")
    for ip, model in served.items():
        try:
            req = urllib.request.Request(
                f"http://{ip}:8000/v1/chat/completions",
                data=json.dumps({"model": model,
                                 "messages": [{"role": "user", "content": "hi"}],
                                 "max_tokens": 1}).encode(),
                headers={"Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=30))
            print(f"  {ip}: fp={d.get('system_fingerprint')} model={d.get('model')}")
        except Exception as exc:                       # noqa: BLE001
            print(f"  {ip}: FAIL {str(exc)[:80]}")


def node_inventory():
    sys.path.insert(0, PVE_DIR)
    try:
        import pve                                    # noqa: PLC0415
    except Exception as exc:                          # noqa: BLE001
        sys.exit(f"cannot import pve.py from {PVE_DIR}: {exc}")
    cmd = ("hostname; echo '@@UNITS'; for u in $(systemctl list-units "
           "--type=service --no-legend | awk '{print $1}' | grep -iE 'vllm|llama'); "
           "do echo \"U:$u enabled=$(systemctl is-enabled $u 2>/dev/null) "
           "active=$(systemctl is-active $u 2>/dev/null) "
           "restarts=$(systemctl show -p NRestarts --value $u)\"; "
           "systemctl show -p ExecStart $u; done; "
           "echo '@@GPU'; nvidia-smi --query-gpu=index,name,memory.total,memory.used "
           "--format=csv,noheader; echo '@@MEM'; free -g | head -2")
    for ip, (node, vmid) in NODES.items():
        print(f"\n########## {ip} (VM{vmid} @ {node})")
        try:
            out, err, _ = pve.guest_exec(node, vmid, ["bash", "-lc", cmd], timeout=90)
            print((out or err)[:2200])
        except Exception as exc:                      # noqa: BLE001
            print(f"  guest-exec failed: {exc}")
    print("\n### PVE VM configs")
    for ip, (node, vmid) in NODES.items():
        try:
            c = pve.api("GET",
                        f"/api2/json/nodes/{node}/qemu/{vmid}/config")["data"]
            print(f"  VM{vmid:<4} {c.get('name','?'):28} cores={c.get('cores')} "
                  f"mem={int(c.get('memory',0))//1024}G balloon={c.get('balloon')} "
                  f"pci={c.get('hostpci0')},{c.get('hostpci1')}")
        except Exception as exc:                      # noqa: BLE001
            print(f"  VM{vmid}: {exc}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", action="store_true",
                    help="also dump per-VM ExecStart/GPU inventory via PVE guest-exec")
    ap.add_argument("--direct", action="store_true",
                    help="also probe each GPU VM directly on :8000")
    args = ap.parse_args()

    key = agent_key()
    routing_map(key)
    if args.direct:
        node_fingerprints()
    if args.nodes:
        node_inventory()
    print("\nread-only probe complete; no service was modified")
