---
name: youtube-content
description: "YouTube transcripts to summaries, threads, blogs."
---

# YouTube Content Tool

## When to use

Use when the user shares a YouTube URL or video link, asks to summarize a video, requests a transcript, or wants to extract and reformat content from any YouTube video. Transforms transcripts into structured content (chapters, summaries, threads, blog posts).

Extract transcripts from YouTube videos and convert them into useful formats.

## Setup

```bash
pip install youtube-transcript-api
```

If the active Python environment has no `pip` or user-site installs are hidden inside a virtualenv, use `uv` instead of stopping:

```bash
uv run --with youtube-transcript-api python SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps
```

For Fabric's built-in YouTube support, ensure `yt-dlp` is on the active PATH. If `yt-dlp` is missing and `uv` is available:

```bash
uv tool install yt-dlp
export PATH="$HOME/.local/bin:$PATH"
```

## Helper Script

`SKILL_DIR` is the directory containing this SKILL.md file. The script accepts any standard YouTube URL format, short links (youtu.be), shorts, embeds, live links, or a raw 11-character video ID.

```bash
# JSON output with metadata
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text (good for piping into further processing)
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only

# With timestamps
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps

# Specific language with fallback chain
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --language tr,en
```

## Output Formats

After fetching the transcript, format it based on what the user asks for:

- **Chapters**: Group by topic shifts, output timestamped chapter list
- **Summary**: Concise 5-10 sentence overview of the entire video
- **Chapter summaries**: Chapters with a short paragraph summary for each
- **Thread**: Twitter/X thread format — numbered posts, each under 280 chars
- **Blog post**: Full article with title, sections, and key takeaways
- **Quotes**: Notable quotes with timestamps
- **Knowledge-repo log**: source folder with metadata, transcript or attempt logs, and extracted knowledge. See `references/youtube-transcript-blockers-and-fabric-fallbacks.md` for a blocked-transcript logging pattern.

### Example — Chapters Output

```
00:00 Introduction — host opens with the problem statement
03:45 Background — prior work and why existing solutions fall short
12:20 Core method — walkthrough of the proposed approach
24:10 Results — benchmark comparisons and key takeaways
31:55 Q&A — audience questions on scalability and next steps
```

## Workflow

1. **Fetch** the transcript using the helper script with `--text-only --timestamps`.
2. **Validate**: confirm the output is non-empty and in the expected language. Also inspect the first bytes/lines for JSON error objects like `{"error": ...}`; the helper can emit an error JSON to stdout with exit code 0, so non-empty output alone does **not** prove transcript recovery. If empty or an error object, retry without `--language` to get any available transcript, then proceed to fallbacks before telling the user transcripts are unavailable.
3. **Fallbacks**: if the helper is blocked, try Fabric/yt-dlp transcript extraction (`fabric -y URL --transcript-with-timestamps`) after confirming `yt-dlp` is installed and on PATH. If normal `yt-dlp` is blocked by YouTube 429/bot checks, try metadata-only extraction with an alternate player client; this can still expose `automatic_captions` timedtext URLs even when subtitle downloads fail:
   ```bash
   yt-dlp --extractor-args "youtube:player_client=android" --skip-download --dump-json "URL" > /tmp/video_meta.json
   python3 - <<'PY'
   import json, re, urllib.request
   d=json.load(open('/tmp/video_meta.json'))
   caps=d.get('automatic_captions') or {}
   urls=[]
   if 'en' in caps:
       urls=[x['url'] for x in caps['en'] if x.get('ext')=='json3']
   else:
       for arr in caps.values():
           for x in arr:
               if x.get('ext')=='json3' and 'lang=en' in x.get('url',''):
                   urls.append(re.sub(r'&tlang=[^&]+','',x['url'])); break
           if urls: break
   data=urllib.request.urlopen(urllib.request.Request(urls[0], headers={'User-Agent':'Mozilla/5.0'}), timeout=30).read().decode('utf-8','ignore')
   open('/tmp/captions.json3','w').write(data)
   PY
   ```
   Convert JSON3 to timestamped text by joining each event's `segs[].utf8` and formatting `tStartMs`. If YouTube blocks all paths, do not hallucinate video-specific content; log metadata, error outputs, and next steps.
4. **Run Fabric on the recovered transcript**: Fabric's YouTube fetch path and Fabric's model/pattern path can fail independently. If `fabric -y URL --transcript-with-timestamps` is blocked by YouTube, still run the requested Fabric pattern on any transcript recovered by another method:
   ```bash
   HOME=/home/miam fabric -p extract_wisdom < /tmp/transcript_with_timestamps.txt > /tmp/fabric_extract_wisdom_raw.md
   ```
   Save both the failed Fabric YouTube attempt and the successful/failed pattern output in the knowledge-repo artifact folder.
5. **Fabric auth failures**: if Fabric's configured model provider is expired/revoked, still capture the attempted command output and consider `fabric -p <pattern> --dry-run < transcript.txt` to prove the pattern/prompt that would have been sent; do not claim the model extraction succeeded. Re-test Fabric pattern execution on each session rather than assuming a prior Codex/auth failure is still current.
6. **Knowledge repo artifact pattern**: when storing YouTube extraction in `jordatech/knowledge_extraction`, use `youtube_logs/videos/<VIDEO_ID>/` with `extracted_knowledge.md`, `metadata.json`, transcript files, raw Fabric output, and attempt logs. See `references/youtube-knowledge-repo-artifacts.md`. For multi-video batches, also create a batch index and follow `references/batch-youtube-knowledge-extraction.md`.
7. **Chunk if needed**: if the transcript exceeds ~50K characters, split into overlapping chunks (~40K with 2K overlap) and summarize each chunk before merging.
8. **Transform** into the requested output format. If the user did not specify a format, default to a summary.
9. **Verify**: re-read the transformed output to check for coherence, correct timestamps, and completeness before presenting.

## Error Handling

See also `references/youtube-transcript-blocked-logging.md` for the durable logging pattern when YouTube transcript extraction is blocked by rate limits/IP/bot protection. For a proven workaround where `yt-dlp --extractor-args "youtube:player_client=android" --dump-json` exposes `automatic_captions` timedtext URLs despite 429/bot blocks, see `references/youtube-timedtext-json3-fallback.md`. For a concrete session example where Fabric's URL transcript fetch failed but Fabric pattern extraction succeeded on a recovered transcript, see `references/session-hermes-openclaw-discord-extraction.md`.

- **Transcript disabled**: tell the user; suggest they check if subtitles are available on the video page.
- **Private/unavailable video**: relay the error and ask the user to verify the URL.
- **No matching language**: retry without `--language` to fetch any available transcript, then note the actual language to the user.
- **Dependency missing**: run `pip install youtube-transcript-api` and retry.
- **YouTube IP/rate-limit/bot protection**: retry with multiple methods before giving up: helper script, `yt-dlp --skip-download --write-auto-subs --sub-lang en --sub-format vtt`, Fabric `-y URL --transcript-with-timestamps`, or an Invidious captions endpoint. If all methods are blocked, log source metadata and raw failure outputs, do not invent detailed video-specific claims, and ask for a pasted transcript/captions file or explicit permission to use browser cookies. Never commit cookies, browser sessions, API keys, or secrets.
- **Fabric YouTube says yt-dlp is missing**: install it with `uv tool install yt-dlp` and add the uv tool bin directory to PATH for that command.
- Fabric model auth expired: log the blocker (`fabric --setup` needed) and continue with transcript retrieval or metadata logging; do not claim Fabric extraction succeeded.
- **Fabric config hidden by sandbox HOME**: Hermes profile HOME may not contain Fabric patterns/provider config. Before concluding Fabric has no patterns or auth, retry commands with the real user home, e.g. `HOME=/home/$USER fabric -l` and `HOME=/home/$USER fabric -p extract_wisdom_with_attribution < transcript.txt`.
- **Secret-scan false positives**: when scanning generated YouTube artifacts, avoid broad regex terms like `sk-` alone because ordinary transcript text can include words like `kiosk-style`; use token-like patterns such as `sk-[A-Za-z0-9]{32,}`.
