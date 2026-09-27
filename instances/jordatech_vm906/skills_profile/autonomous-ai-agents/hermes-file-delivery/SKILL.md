---
name: hermes-file-delivery
description: "Deliver files to the user through Hermes messaging platforms (Telegram etc.) — MEDIA:<path> tag in the final reply, MEDIA_DELIVERY_EXTS extension allowlist (.md works), [[as_document]] directive, adapter send paths, troubleshooting."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, telegram, file-delivery, gateway, handoff]
---

# Hermes File Delivery (messaging platforms)

Class of task: the user asks for a file (handoff .md, report, artifact) to be
"uploaded to Telegram so I can download it on my phone". The mechanism is NOT a
send tool — it is a **tag in your final reply** that the gateway parses after
the text is delivered.

## The mechanism (verified in gateway source, 2026-09-26)

1. Put a literal tag line in your FINAL assistant response:

       MEDIA:/absolute/path/to/file.md

   - Absolute path, real file, extension from the allowlist below.
   - The gateway's `_deliver_media_from_response` (gateway/run.py) extracts
     tags via `adapter.extract_media` and sends each file through the platform
     adapter (`send_document` for doc-like files; images go sendPhoto unless
     `[[as_document]]` is present anywhere in the reply).
   - Keep the tag on its own line; optional one-line lead-in text is fine
     (text streams first, then the attachment arrives).

2. Extension allowlist = `MEDIA_DELIVERY_EXTS` in
   `gateway/platforms/base.py` (~line 1401). Includes **.md**, .txt, .pdf,
   .csv, .json, .yaml, .zip, images/audio/video, .html. If your extension is
   missing, copy/transcode to a listed one (e.g. `.md` → fine as-is; unknown
   binary → zip it).

3. Directives you may combine in the same reply:
   - `[[as_document]]` — deliver image-extension files as lossless documents
     (sendDocument) instead of recompressed photos. All-or-nothing per reply.
   - `[[audio_as_voice]]` — TTS/audio delivered as a voice bubble.

## Pitfalls

- **"Send this over Telegram" ≠ find a send tool.** There is no dedicated send-message tool for most platforms — tool_search for 'telegram send document' returns only third-party MCP noise (Zapier Slack/Gmail/etc.). Burning 4+ round-trips hunting for one is the classic failure (2026-09-27). The mechanism IS the MEDIA: tag in your final reply. To confirm the destination is live, read `~/.hermes/profiles/<profile>/channel_directory.json` — `platforms.telegram[]` carries `{id, name, type, thread_id}` for each known chat (the home DM shows as type `dm`); use it to verify the target exists instead of guessing chat IDs.
- **Prose mentions don't deliver.** The tag must appear as a real `MEDIA:`
  token in the final reply — writing "the file is at /path/file.md" does
  nothing. Conversely, never write `MEDIA:` with a fake path in prose
  (docs, examples) — masked spans (code blocks, JSON strings) are protected,
  but bare ones in plain text WILL fire a delivery of a nonexistent path.
- **Auto-append only fires for producer tools** (`text_to_speech`,
  `image_generate`) whose tool RESULTS contain MEDIA: lines. A MEDIA: line in
  a generic tool result or a non-producer tool's output is NOT auto-appended —
  emit the tag yourself in the final reply.
- **Files must exist at send time** on the gateway host; the adapter fails the
  attachment silently (logged warning) if the path is missing — verify the
  file was actually written (skill: file-write-verification) before tagging.
- Large files: Telegram bots cap documents at 50 MB via the standard API.
- The tag is STRIPPED from user-visible text — don't also describe it as a
  link in the same line.

## Where this lives in source (for future re-verification)

- `gateway/run.py` — `_deliver_media_from_response`, `_TOOL_MEDIA_RE`
  (tool-result auto-append matcher), `_AUTO_APPEND_MEDIA_TOOL_NAMES`.
- `gateway/platforms/base.py` — `extract_media` (~3358), `MEDIA_DELIVERY_EXTS`
  (~1401), protected-span masking.
- `plugins/platforms/telegram/adapter.py` — `send_document` (~5429),
  `send_image_file`, `send_voice` (dm-topic reply-anchor retry wrapper).

## Relationship to other skills

- Jordan deliverable workflow (see acms-project-operations): single .md handoff
  in the work folder → summary in chat → MEDIA: line for phone download.
- `hermes-agent` (bundled, authoritative for config/platform setup) does not
  cover this delivery path as of 2026-09-26; if the gateway changes, re-grep
  the source paths above before trusting this doc.
