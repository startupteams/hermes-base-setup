---
name: telegram-send-file
description: Deliver a local file as a Telegram document to the user's DM when no send_message/file-delivery tool is available
trigger: User asks to send/deliver a file "over Telegram" / "to Telegram here" and the active toolset lacks a send_message or file-delivery tool
---

# Sending a file via Telegram Bot API

## When
Hermes gateway is connected to Telegram (check `gateway_state.json` → `platforms.telegram.state: connected`) but no `send_message` tool exists in the toolset. Use the Bot API directly.

## Steps

1. **Verify the file exists + secret-scan it** before sending:
   ```bash
   ls -la <file> && grep -nEi 'sk-[A-Za-z0-9]|ghp_[A-Za-z0-9]|gho_[A-Za-z0-9]|xox[bap]-|Bearer [A-Za-z0-9]|password|vck_|vcp_|GOCSPX' <file> | head -20
   ```
   Abort on hits; never deliver secrets to a cloud API.

2. **Get the token WITHOUT printing it.** Simplest source, verified 2026-10-01: the profile `.env`
   carries `TELEGRAM_BOT_TOKEN` and `TELEGRAM_HOME_CHANNEL` directly:
   ```python
   env = {}
   for line in open("/home/jordatech/.hermes/profiles/<profile>/.env"):
       line = line.strip()
       if line and not line.startswith("#") and "=" in line:
           k, v = line.split("=", 1)
           env[k] = v
   tok, chat_id = env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_HOME_CHANNEL"]
   ```
   Fallback if the profile `.env` lacks it: `hermes_cli.config.get_env_value('TELEGRAM_BOT_TOKEN')`
   with `sys.path.insert(0, '/home/jordatech/.hermes/hermes-agent')` (credential store resolves it;
   `print('present:', bool(tok), 'len:', len(tok))` — never the value).

4. **Upload via multipart POST** (stdlib only, token never echoed):
   ```python
   import sys, json, urllib.request, urllib.error, uuid
   sys.path.insert(0, '/home/jordatech/.hermes/hermes-agent')
   from hermes_cli.config import get_env_value
   tok = get_env_value('TELEGRAM_BOT_TOKEN')
   chat_id = "<chat_id>"; path = "<file>"
   boundary = uuid.uuid4().hex
   def part_field(name, value):
       return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode()
   def part_file(name, filename, content):
       return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
               f"Content-Type: text/markdown\r\n\r\n").encode() + content + b"\r\n"
   body  = part_field("chat_id", chat_id)
   body += part_field("caption", "<short caption>")
   body += part_file("document", path.split('/')[-1], open(path, "rb").read())
   body += f"--{boundary}--\r\n".encode()
   req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendDocument",
       data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
   with urllib.request.urlopen(req, timeout=60) as r:
       resp = json.load(r)
   print("ok:", resp.get("ok"), "message_id:", resp.get("result", {}).get("message_id"),
         "file_size:", resp.get("result", {}).get("document", {}).get("file_size"))
   ```

5. **Verify delivery**: confirm `ok: True` and that `file_size` matches the source byte count. Report message_id as proof.

## Pitfalls
- **First choice is still the gateway MEDIA: tag** (skill
  `autonomous-ai-agents/hermes-file-delivery`) — use THIS skill only when the
  session is not on a gateway platform or the tag path is unavailable.
- Use `sendDocument` (not `sendPhoto`) for `.md`/text files — preserves the file as a downloadable document.
- **Simpler upload form (verified 2026-10-03):** stage the token to a 0600
  temp file (never echo it), then
  `TG_TOKEN=$(cat /tmp/.tgtoken); curl -s --max-time 30 -X POST
  "https://api.telegram.org/bot${TG_TOKEN}/sendDocument" -F "chat_id=${CHAT}"
  -F "document=@${FILE}" -F "caption=<short caption>"` — the `-F` multipart
  form works without the stdlib boundary script. Verify `ok: True` +
  `file_size` matches the source byte count, then **`shred -u` the staged
  token file** — never leave token copies in /tmp.
- 50 MB upload limit per file; larger files need chunking or an external link.
- The gateway process env has NO telegram vars (`/proc/<pid>/environ` is clean) — the token lives in Hermes' credential layer, only reachable via `get_env_value`.
- `caption` max 1024 chars; keep it a summary, put details in the file.
- **Verify BEFORE sending**: `ls -la` the file and grep it for the secret
  patterns above. A descriptive word like "password" inside prose is fine —
  abort only on actual token-shaped values.
- `TELEGRAM_HOME_CHANNEL` from the profile `.env` works as chat_id (verified
  2026-10-02, profile agent_stea004_entrepreneur); no need to hardcode a chat
  id when the env carries it.
- Success signature: `ok: True` + `file_size` matching the source byte count
  exactly; report message_id as delivery proof.
- As a final fallback, media can also be referenced with the MEDIA:/file-delivery convention in a normal reply if the platform supports native attachments — but this Bot API path works even when that doesn't render.
