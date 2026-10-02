---
name: hermes-file-delivery
description: "Deliver files to the user through Hermes messaging platforms (Telegram etc.). THE mechanism is the MEDIA:<path> tag in your final reply — there is no send tool to search for. FIRST skill to load for any 'send/upload/put this file on Telegram' request. Covers the tag, MEDIA_DELIVERY_EXTS allowlist (.md works), [[as_document]] directive, adapter send paths, troubleshooting."
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

- **"Send this over Telegram" ≠ find a send tool — READ THIS SKILL FIRST.**
  This failure has recurred TWICE (2026-09-28 and again 2026-09-29: multiple
  tool_search round-trips hunting a send tool, two attempts at an unloaded
  `send_message` tool, then a raw Bot API script — while the one-step answer
  was sitting here). When a file-delivery request arrives, the DEFAULT is:
  write/verify the file, then put `MEDIA:<abs-path>` on its own line in the
  final reply. Do not tool_search for send mechanisms. There is a
  `send_message` tool in the codebase (tools/send_message_tool.py, supports
  `MEDIA:<path>` in message text) but it is NOT wired into this profile's
  runtime toolset — do not go looking; the tag path needs nothing.
  **Session-start trigger:** if the request says "send/attach/deliver … over
  Telegram (as a document/file)", load THIS skill before making any tool
  calls about delivery.

- **Last-resort fallback (gateway path unavailable):** Bot API sendDocument
  works from execute_code/terminal — read the active `TELEGRAM_BOT_TOKEN` from
  the profile `.env` (uncommented line; never print it), take the chat_id from
  `TELEGRAM_HOME_CHANNEL` (same file) or `channel_directory.json`, POST
  multipart `sendDocument` with caption. Verify `ok: true` + `message_id` in
  the response. Proven 2026-09-29 (16 KB .md handoff → home chat, doc
  attachment + caption). Note the deliverable then lands OUTSIDE the gateway's
  session history — prefer the tag whenever the gateway is up.
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
