# YouTube blocked extraction fallback

Session-derived pattern for videos where YouTube blocks transcript retrieval from cloud/agent IPs.

## Symptoms observed

- `youtube-transcript-api` returns a request/IP blocked error.
- `yt-dlp` returns HTTP 429, bot confirmation, or asks for cookies.
- Fabric YouTube transcript mode reports rate limiting or missing `yt-dlp`.
- Fabric extraction patterns may fail separately if the configured model auth is expired/revoked.

## Safe fallback workflow

1. Try the skill helper script first:
   ```bash
   uv run --with youtube-transcript-api python /path/to/fetch_transcript.py "$URL" --timestamps
   ```
2. Try `yt-dlp` captions without downloading video:
   ```bash
   yt-dlp --skip-download --write-auto-subs --sub-lang en --sub-format vtt -o '/tmp/video.%(ext)s' "$URL"
   ```
3. Try Fabric transcript extraction if configured:
   ```bash
   HOME=/home/miam fabric -y "$URL" --transcript-with-timestamps
   ```
4. If blocked, fetch metadata that does not require auth when possible:
   ```bash
   python - <<'PY'
   import urllib.parse, urllib.request
   url='https://www.youtube.com/oembed?format=json&url='+urllib.parse.quote('https://www.youtube.com/watch?v=VIDEO_ID')
   print(urllib.request.urlopen(url).read().decode())
   PY
   ```
5. Create a source log with:
   - URL and video ID
   - title/author metadata
   - exact extraction attempts and error logs
   - clear statement that no transcript-specific knowledge was extracted
   - next steps: user-provided transcript, captions file, authorized cookies, or fixed Fabric/model setup

## Guardrails

- Do not commit cookies, browser sessions, API keys, or secrets.
- Do not use browser cookies unless the user explicitly grants permission for that session.
- Do not hallucinate detailed video lessons from title/metadata only.
