# Session note: Hermes + OpenClaw Discord extraction

Source video: `ziSeVy5p9ck` (`How I have my Hermes and OpenClaw AI Agents.. WORKING TOGETHER!`), processed 2026-05-10 for `jordatech/knowledge_extraction`.

## What worked

When normal transcript tools were blocked, `yt-dlp` metadata extraction with the Android client still returned usable `automatic_captions`:

```bash
yt-dlp --extractor-args "youtube:player_client=android" --skip-download --dump-json "$URL" > video_meta_ytdlp.json 2> video_meta_ytdlp.err
```

Then select English `automatic_captions` with `ext == json3`, download the timedtext URL, and convert `events[].segs[].utf8` into timestamped transcript lines.

Fabric's model path worked even though Fabric's YouTube fetch path did not:

```bash
HOME=/home/miam fabric -p extract_wisdom_with_attribution < transcript_with_timestamps.txt > fabric_extract_wisdom_raw.md
```

## Pitfalls observed

- `youtube-transcript-api` helper can emit a JSON error object to stdout and exit cleanly; validate content semantics, not only file size.
- Fabric `-y URL --transcript-with-timestamps` can fail with YouTube rate limits while `fabric -p <pattern> < transcript.txt` still succeeds.
- `yt-dlp --write-auto-subs` can fail with bot/sign-in errors, while `--dump-json` with Android client still exposes caption URLs.
- GitHub push may be blocked in this runtime when no `GITHUB_TOKEN`, `~/.git-credentials`, or `gh auth` session is present. Commit locally and report the exact push command rather than losing work.

## Artifact set used

Store under `youtube_logs/videos/<VIDEO_ID>/`:

- `extracted_knowledge.md`
- `metadata.json`
- `source.md`
- `transcript_with_timestamps.txt`
- `transcript_plain.txt`
- `fabric_extract_wisdom_raw.md`
- `fabric_youtube_transcript_attempt.txt`
- `youtube_transcript_api_initial_stderr.txt`
- `yt_dlp_metadata_stderr.txt`
- `yt_dlp_subtitles_attempt.txt`
- `tool_check.txt`
