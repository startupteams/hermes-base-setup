# YouTube Transcript Blocked: Logging Pattern

Use this when a YouTube task asks for transcript extraction or Fabric knowledge extraction, but automated access is blocked by YouTube rate limits, IP protection, or bot checks.

## Observed failure modes

- `youtube-transcript-api` may return an error saying YouTube is blocking requests from the IP or cloud provider.
- `yt-dlp` may fail with HTTP 429 or `Sign in to confirm you’re not a bot`.
- Fabric `--youtube --transcript-with-timestamps` may report YouTube rate limits or require `yt-dlp` in PATH.
- Fabric model execution can also fail separately if its configured provider login has expired.

## Recovery sequence

1. Try the skill helper script with `youtube-transcript-api`.
2. Try Fabric YouTube transcript mode:
   ```bash
   HOME=/home/miam fabric -y '<youtube-url>' --transcript-with-timestamps
   ```
3. Try `yt-dlp` captions:
   ```bash
   yt-dlp --skip-download --write-auto-subs --sub-lang en --sub-format vtt -o '/tmp/video.%(ext)s' '<youtube-url>'
   ```
4. Optionally try public alternate caption APIs such as Invidious, but treat them as best-effort.
5. If blocked, retrieve non-sensitive metadata if possible, such as YouTube oEmbed:
   ```bash
   python - <<'PY'
   import json, urllib.parse, urllib.request
   url='https://www.youtube.com/oembed?format=json&url='+urllib.parse.quote('https://www.youtube.com/watch?v=VIDEO_ID')
   print(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})).read().decode())
   PY
   ```

## Logging pattern

If the user asked to log YouTube knowledge in a repository, create a durable folder like:

```text
youtube_logs/
  README.md
  videos/<video_id>/
    metadata.json
    source.md
    extracted_knowledge.md
    transcript_attempts.*
    fabric_attempts.*
```

In `extracted_knowledge.md`, clearly distinguish:

- metadata-level facts that were actually retrieved,
- blocked extraction attempts,
- unanswered questions for future extraction,
- next steps to complete extraction from a pasted transcript/captions file or authorized cookie flow.

## Safety rules

- Do not commit cookies, browser sessions, API keys, or private credentials.
- Do not hallucinate detailed video-specific lessons when transcript/video content is unavailable.
- If using browser cookies is necessary, ask explicitly first and avoid storing cookie files in the repo.
