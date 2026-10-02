# Chunked base64 exfil over PVE guest-exec (no SSH)

When the guest has no SSH path and QGA `guest-file-read` is unimplemented, move a capture archive out via the PVE agent API in base64 chunks.

Recipe (source VM, then poll per chunk):

```bash
# on VM, once:
tar czf - <dirs> | sed -E '<pass-1 sanitize rules>' | base64 -w7000 > /tmp/cap.b64
md5sum /tmp/cap.tar.gz   # also keep md5 of pre-base64 tar for verification
wc -l /tmp/cap.b64
```

Per chunk `N` via `pve.py exec` (arg[] style, poll for completion):

```bash
sed -n "$((N*100+1)),$(( (N+1)*100 ))p" /tmp/cap.b64
```

Locally: concatenate chunks in order → `base64 -d` → verify md5 matches → extract → **run the destination-side secret scan (see secret-scan-patterns.md) before git add**.

Notes:
- `-w7000` keeps lines well under QGA/PVE output caps; 100 lines/chunk ≈ 700 KB per call.
- guest-exec via pve.py: `arg[]` array + poll task status; the API is finicky about shell strings — pass argv lists, not `bash -c` blobs, where possible.
- VM114's qga can wedge (known from ops notes): if polls hang, check `qemu-guest-agent` service on the guest before assuming a transfer bug.
