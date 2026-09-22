# DeepAPI YouTube Transcript Extraction

Jordan explicitly requests DeepAPI for video research ("use DeepApi to research..."). Treat a named tool as the primary transcript path for that session; otherwise use DeepAPI as a fallback when youtube-transcript-api / Fabric / yt-dlp hit YouTube bot checks — it scrapes server-side and bypasses them.

## Auth and config

- Env file: `~/.deepapi/env` (chmod 600) contains `export DEEPAPI_API_BASE_URL=...` and `export DEEPAPI_API_KEY=...`. Never echo or store the key.
- In `execute_code` / Python the vars are NOT inherited from the shell rc — parse the file directly, stripping the `export ` prefix:

  ```python
  env = {}
  for line in open(os.path.expanduser("~/.deepapi/env")):
      line = line.strip()
      if line.startswith("export ") and "=" in line:
          k, v = line[len("export "):].split("=", 1)
          env[k.strip()] = v.strip().strip('"').strip("'")
  ```

- Endpoint discovery: `GET /v1` lists every endpoint with method/description. There is no `/v1/models`; unknown paths return `{"error":{"code":"unknown_capability", "hint":"Use a documented endpoint path — GET /v1 lists every endpoint."}}`.

## Transcript request

`POST {base}/v1/scrape/youtube/transcript`

Headers (all required):
- `Authorization: Bearer <key>`
- `Content-Type: application/json`
- `Idempotency-Key: <unique uuid4 per call>` — REQUIRED. Missing it fails with `{"error":{"code":"missing_idempotency_key"}}`.

Body: `{"url": "https://www.youtube.com/watch?v=<VIDEO_ID>"}`

## Response shape

```json
{
  "route": "/v1/scrape/youtube/transcript",
  "status": "succeeded",
  "output": [{
    "text": "<full plain transcript>",
    "segments": [{"startSecs": 0.001, "durationSecs": 4.639, "text": "..."}]
  }],
  "list": {"resultCount": 1, "hasMore": false, "listState": "results"},
  "balance": {"postedDebitsMicrousd": 6743741, "availableMicrousd": 117881259},
  "error": null
}
```

- `output` is a LIST — the transcript object is `output[0]`.
- **Timestamps are float SECONDS** (`startSecs`), not milliseconds. Format `[MM:SS]` (or `[HH:MM:SS]` when `startSecs >= 3600`) directly from `startSecs`. Assuming milliseconds produces `[??:??]` junk and forces a rebuild from the raw JSON (verified failure mode, 2026-09-11).
- Caption-less videos return an empty result. Always check `status` and `error` before trusting output.
- Cost is negligible per video (three transcripts, ~82K chars total, debited ≈ 6.7 microusd), but check `balance` when batching large.

## Knowledge-repo artifacts (jordatech/knowledge_extraction)

Save per video folder (`youtube_logs/videos/<VIDEO_ID>/`):
- `deepapi_transcript_raw.json` — full API response (audit trail)
- `transcript_plain.txt` — `output[0]["text"]`
- `transcript_with_timestamps.txt` — one `[MM:SS] text` line per segment
- `metadata.json` — title/channel from free oEmbed (`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<ID>&format=json`) plus `"transcript_source": "deepapi /v1/scrape/youtube/transcript"`

## Session-proven script skeleton

```python
import json, os, subprocess, uuid

env = {}
for line in open(os.path.expanduser("~/.deepapi/env")):
    line = line.strip()
    if line.startswith("export ") and "=" in line:
        k, v = line[len("export "):].split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

def call(body):
    return subprocess.run(
        ["curl", "-s", "--max-time", "180",
         f"{env['DEEPAPI_API_BASE_URL']}/v1/scrape/youtube/transcript",
         "-H", f"Authorization: Bearer {env['DEEPAPI_API_KEY']}",
         "-H", "Content-Type: application/json",
         "-H", f"Idempotency-Key: {uuid.uuid4()}",
         "-d", json.dumps(body)],
        capture_output=True, text=True, timeout=200).stdout

d = json.loads(call({"url": "https://www.youtube.com/watch?v=<ID>"}))
assert d.get("status") == "succeeded" and d.get("output"), d.get("error")
segs = d["output"][0]["segments"]
def fmt(sec):
    h, rem = divmod(int(sec), 3600); m, s = divmod(rem, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]" if h else f"[{m:02d}:{s:02d}]"
ts = "\n".join(fmt(s["startSecs"]) + " " + s["text"].strip() for s in segs)
```
