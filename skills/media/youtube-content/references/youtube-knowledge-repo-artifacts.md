# YouTube Knowledge Repository Artifact Pattern

Use this when the user asks to extract knowledge from a YouTube video and store it in `jordatech/knowledge_extraction`.

## Folder layout

Store each video under:

```text
youtube_logs/videos/<VIDEO_ID>/
  extracted_knowledge.md              # final human-readable extraction
  metadata.json                        # yt-dlp dump-json metadata when available
  transcript_with_timestamps.txt       # recovered transcript with [MM:SS] lines
  transcript_plain.txt                 # plain transcript for model input/search
  fabric_extract_wisdom_raw.md         # raw Fabric pattern output when it succeeds
  fabric_extract_wisdom_attempt.txt    # Fabric pattern error output when it fails
  fabric_extract_wisdom_dry_run.txt    # optional dry-run proving the pattern prompt
  fabric_youtube_transcript_attempt.txt# Fabric -y transcript fetch attempt
  youtube_transcript_api_attempt.txt   # helper/API transcript attempt
  yt_dlp_metadata_stderr.txt           # yt-dlp warnings/errors for metadata fallback
```

Not every file is required; include the files that were produced. Do not store cookies, browser session files, API keys, or secrets.

## Recommended extraction sequence

1. Verify the repo origin is `https://github.com/jordatech/knowledge_extraction.git` and the branch is `c01entrepreneur_bot`.
2. Try `youtube-transcript-api` helper first and save the attempt output.
3. Try Fabric YouTube transcript extraction and save the attempt output:
   ```bash
   HOME=/home/miam fabric -y "$URL" --transcript-with-timestamps > fabric_youtube_transcript_attempt.txt 2>&1 || true
   ```
4. If YouTube blocks normal transcript paths, use the `yt-dlp --extractor-args "youtube:player_client=android" --dump-json` fallback to recover `automatic_captions` timedtext URLs.
5. Convert JSON3 captions to timestamped transcript.
6. Run the requested Fabric pattern on the recovered transcript even if Fabric's YouTube transcript path failed:
   ```bash
   HOME=/home/miam fabric -p extract_wisdom < transcript_with_timestamps.txt > fabric_extract_wisdom_raw.md 2>&1 || true
   ```
7. Create `extracted_knowledge.md` with source metadata, extraction status, concise synthesis, and the raw Fabric output when appropriate.
8. Verify required sections/terms by reading the final file back.
9. Commit and push the artifact folder to `c01entrepreneur_bot`.

## Pitfalls

- Fabric's YouTube fetch can fail while Fabric pattern execution succeeds. Treat these as separate paths.
- Fabric auth/provider failures can change between sessions. Re-test instead of assuming prior failures still apply.
- The terminal tool may reject commands containing unescaped `&` in shell strings; avoid inline URLs with raw ampersands in shell commands or quote/sanitize them carefully.
- Auto-captions can mishear technical names. Add a caveat when model/library names are inferred from noisy captions.
