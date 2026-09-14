# Batch YouTube Knowledge Extraction to `jordatech/knowledge_extraction`

Use this when the user provides multiple YouTube URLs and asks to analyze them, use Fabric, and document results in the knowledge extraction repo.

## Proven workflow

1. **Repo setup**
   - Clone/fetch `https://github.com/jordatech/knowledge_extraction.git`.
   - Ensure branch is `c01entrepreneur_bot` before writing.
   - If GitHub auth fails in the profile HOME, retry git operations with the real home, e.g. `HOME=/home/$USER git clone ...`.

2. **Per-video artifact directory**
   - Use `youtube_logs/videos/<VIDEO_ID>/`.
   - Write `source.md` immediately with requested label, URL, and video ID.
   - Save `metadata.json`, transcript files, Fabric attempt logs, raw Fabric output, and final `extracted_knowledge.md`.

3. **Transcript and metadata retrieval**
   - Try the YouTube transcript helper first and save stdout/stderr attempt files.
   - Use `yt-dlp --extractor-args "youtube:player_client=android" --skip-download --dump-json "$URL"` for metadata and fallback captions.
   - If helper transcripts fail but metadata includes `automatic_captions`, fetch the English `json3` timedtext URL and convert events to `[HH:MM:SS] text` lines.

4. **Fabric execution**
   - Run Fabric with the real HOME when profile HOME lacks Fabric/GitHub/provider config:
     ```bash
     HOME=/home/$USER fabric -p extract_wisdom_with_attribution < transcript_with_timestamps.txt > fabric_extract_wisdom_raw.md 2> fabric_extract_wisdom_attempt.txt
     ```
   - Also attempt direct Fabric YouTube retrieval for audit:
     ```bash
     HOME=/home/$USER fabric -y "$URL" --transcript-with-timestamps > fabric_youtube_transcript_attempt.txt 2>&1 || true
     ```
   - Keep Fabric's YouTube retrieval path separate from Fabric's pattern path; one can fail while the other succeeds.

5. **Final document shape**
   - Include YAML frontmatter with title, source URL, video ID, channel, extraction date, and tags.
   - Include sections: Source, Extraction method and status, High-level knowledge capture, One-sentence takeaway, Key insights, Technical facts, Practical recommendations, Tools/platforms/concepts referenced, How this knowledge may be useful, and raw Fabric output.
   - For a batch, add a collection index such as `youtube_logs/batch_<date>_<topic>_index.md` linking each `extracted_knowledge.md` and summarizing cross-video themes.

## Validation checklist

- Each target video has non-empty `transcript_with_timestamps.txt`, `fabric_extract_wisdom_raw.md`, and `extracted_knowledge.md`.
- `extracted_knowledge.md` contains `## Source` and a Fabric-output section.
- Re-read at least one final file for formatting and obvious caption/model-name errors.
- Run a targeted secret scan before commit. Avoid over-broad patterns like plain `sk-` because normal words such as “kiosk-style” can false-positive; prefer anchored token-like regexes such as `sk-[A-Za-z0-9]{32,}`.
- Commit and push to `c01entrepreneur_bot` after validation.

## Pitfalls

- Fabric may be installed/configured under `/home/<user>` while Hermes profile HOME is sandboxed. Use `HOME=/home/$USER` for Fabric and git if needed.
- Auto-captions may distort product/model names. Preserve source artifacts and avoid overclaiming when the transcript is noisy.
- `fabric -l` may appear empty if HOME points at the profile sandbox; test with the real HOME before assuming patterns are unavailable.
