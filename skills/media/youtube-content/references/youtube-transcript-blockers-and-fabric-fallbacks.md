# YouTube Transcript Blockers and Fabric Fallbacks

Session-derived notes from logging a YouTube video into `knowledge_extraction/youtube_logs` for local LLM research.

## Symptoms observed

- `youtube-transcript-api` can fail even when the video exists and oEmbed metadata is reachable:
  - YouTube reports IP/request protection or cloud-provider blocking.
- `yt-dlp` can fail with HTTP 429 or "Sign in to confirm you’re not a bot."
- Fabric YouTube transcript mode may fail before extraction if `yt-dlp` is not on PATH:
  - `yt-dlp not found in PATH. Please install yt-dlp to use YouTube transcript functionality`
- Fabric model/pattern execution may fail separately from transcript retrieval when auth is stale:
  - `Codex login has expired or been revoked. Please rerun 'fabric --setup'.`
- YouTube oEmbed may still work for metadata:
  - `https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=<VIDEO_ID>`

## Useful fallback sequence

1. Try the skill helper:
   ```bash
   python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps
   ```
2. If pip/dependency setup is unavailable, run through uv:
   ```bash
   uv run --with youtube-transcript-api python SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps
   ```
3. Try Fabric/yt-dlp:
   ```bash
   HOME=/home/miam fabric -y "URL" --transcript-with-timestamps
   ```
4. If Fabric says `yt-dlp` is missing:
   ```bash
   uv tool install yt-dlp
   export PATH="$HOME/.local/bin:$PATH"
   ```
5. If YouTube blocks all automated transcript paths, retrieve oEmbed metadata and log blockers instead of hallucinating:
   ```bash
   python - <<'PY'
   import urllib.parse, urllib.request
   video='https://www.youtube.com/watch?v=VIDEO_ID'
   url='https://www.youtube.com/oembed?format=json&url='+urllib.parse.quote(video)
   print(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})).read().decode())
   PY
   ```

## Logging pattern for knowledge repositories

When transcript extraction is blocked but the user asked to log the source:

- Create a source folder such as `youtube_logs/videos/<video_id>/`.
- Save `metadata.json` from oEmbed where possible.
- Save `source.md` with URL, title, author, context, and collection status.
- Save raw attempt logs such as `fabric_youtube_transcript_attempt.txt` and `youtube_transcript_api_attempt.json`.
- Create `extracted_knowledge.md` only with metadata-level facts and explicit blockers. Do not write detailed video-specific claims unless transcript/content was actually available.
- State next steps: pasted transcript, `.vtt`/`.srt`, cookies permission, YouTube API setup, or rerun `fabric --setup`.

## Safety notes

- Do not commit cookies, browser sessions, API keys, or private credentials.
- If using browser cookies is necessary, ask the user first and avoid committing generated cookie files.
- Treat bot/rate-limit failures as an access problem, not as evidence that transcripts are disabled.
