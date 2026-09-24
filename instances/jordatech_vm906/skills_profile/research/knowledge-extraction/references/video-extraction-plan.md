# Video Extraction Plan

Use this as a generic plan for extracting knowledge from one or more educational videos.

## Source list format

Capture a label and URL for every source before processing:

```text
<label> | <youtube-or-source-url>
```

For YouTube batches, derive the video ID and create `youtube_logs/videos/<VIDEO_ID>/source.md` immediately so the repository records what was requested even if transcript retrieval is blocked.

## Extraction schedule

- [ ] Capture source labels, URLs, and IDs.
- [ ] Fetch metadata and transcripts, preferring timestamped transcripts.
- [ ] Save raw attempt logs for transcript and Fabric calls.
- [ ] Run the relevant Fabric pattern on the transcript; `extract_wisdom_with_attribution` works well for technical videos where source traceability matters.
- [ ] Create a final `extracted_knowledge.md` for each source.
- [ ] For batches, create an index file linking all extracted knowledge docs and summarizing cross-source themes.
- [ ] Validate file presence, formatting, and absence of secrets before committing.

## Knowledge structure

Each final extraction should include:

- source metadata and attribution
- extraction method/status
- high-level knowledge capture
- key insights
- technical facts / implementation details
- practical recommendations
- tools, platforms, and concepts referenced
- raw Fabric output or a pointer to it

## References

- `youtube-content/references/youtube-knowledge-repo-artifacts.md`
- `youtube-content/references/batch-youtube-knowledge-extraction.md`
