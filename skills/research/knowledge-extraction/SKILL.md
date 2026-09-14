---
name: knowledge-extraction
description: Extract and document knowledge from various sources (YouTube, articles, etc.) using structured approaches and fabric patterns
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [knowledge, extraction, research, documentation, fabric]
    related_skills: [github-repo-management, fabric-pattern-authoring]
---

# Knowledge Extraction System

A systematic approach to extract, organize, and document knowledge from various sources including YouTube videos, articles, podcasts, and other educational content.

## When to Use This Skill

- You need to extract key concepts from educational YouTube videos
- You want to create structured documentation from learning materials
- You're building a knowledge base for future reference
- You need to synthesize information from multiple sources
- You want to apply consistent formatting to extracted knowledge
- The user provides documents/archives and asks for researched answers saved as markdown in a Git-backed knowledge repository
- The user asks for public-web people sourcing, candidate discovery, or recruiter-style shortlists that need verifiable evidence from LinkedIn and adjacent public sources

## Core Principles

1. **Atomic Knowledge**: Break down complex topics into discrete, understandable concepts
2. **Source Attribution**: Always credit the original source with timestamps and links
3. **Actionable Insights**: Focus on practical, applicable knowledge over theory
4. **Cross-Referencing**: Link related concepts across different sources
5. **Progressive Disclosure**: Provide both quick summaries and deep dives

## Workflow Overview

1. **Source Identification**: Identify and gather source materials
2. **Initial Review**: Watch/read material to identify key sections
3. **Timestamped Extraction**: Extract concepts with precise timestamps
4. **Concept Decomposition**: Break down complex ideas into simpler components
5. **Knowledge Structuring**: Organize extracted knowledge using templates
6. **Validation & Review**: Verify accuracy and completeness
7. **Documentation**: Create final markdown files in knowledge repository
8. **Version Control**: Commit and push changes to GitHub

## Detailed Steps

### 1. Source Preparation

```bash
# Create workspace for extraction
mkdir -p /tmp/knowledge_extraction
cd /tmp/knowledge_extraction

# Save source URLs for reference. For batches, include a human label per URL.
cat > sources.txt << 'EOF'
Docker concepts | https://www.youtube.com/watch?v=ObhdD49AEYw
AI Server setup with Proxmox | https://www.youtube.com/watch?v=kB9a5nXCwkA
EOF
```

For YouTube batches destined for `jordatech/knowledge_extraction`, use the `youtube-content` skill's `references/batch-youtube-knowledge-extraction.md` artifact pattern: one folder per video under `youtube_logs/videos/<VIDEO_ID>/`, plus a batch index linking all final `extracted_knowledge.md` files.

### 2. Fabric-Based Knowledge Extraction

Use fabric patterns to extract structured knowledge:

```bash
# Install fabric if not present (if needed)
# curl -sSL https://github.com/danielmiessler/fabric/releases/latest/download/fabric-linux-amd64 -o /usr/local/bin/fabric
# chmod +x /usr/local/bin/fabric

# Extract knowledge using YouTube transcript pattern
# Note: This assumes youtube-transcript-api or similar is available
python3 -c "
import requests
import re
from urllib.parse import urlparse, parse_qs

def extract_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['youtu.be', 'www.youtu.be']:
        return parsed_url.path[1:]
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
        if parsed_url.path[:7] == '/embed/':
            return parsed_url.path.split('/')[2]
        if parsed_url.path[:3] == '/v/':
            return parsed_url.path.split('/')[2]
    return None

# Process each source
with open('sources.txt', 'r') as f:
    urls = [line.strip() for line in f if line.strip()]

for url in urls:
    video_id = extract_video_id(url)
    print(f'Processing video: {video_id}')
    # In real implementation, would fetch transcript and extract knowledge
"
```

When Fabric is unavailable, or the user names a specific tool (e.g., DeepAPI), fetch the transcript with that tool and either run Fabric on the recovered text or synthesize the extraction directly. Record the actual method in the final file's "Extraction method and status" section and keep the raw tool response (e.g., `deepapi_transcript_raw.json`) in the artifact folder. For DeepAPI transcript retrieval, see `references/deepapi-transcript-extraction.md` in this skill (unique `Idempotency-Key` header required; segments use float `startSecs` seconds).

### 3. Knowledge Structure Template

Each extracted knowledge unit should follow this structure:

```markdown
# [Concept Title]

**Source**: [Video Title] ([URL])
**Timestamp**: [HH:MM:SS] 
**Extracted On**: [DATE]

## Core Concept
[Clear, concise explanation of the concept in 1-2 sentences]

## Key Points
- [Bullet point 1]
- [Bullet point 2]
- [Bullet point 3]

## Technical Details
[Any specific commands, configurations, or technical specifications]

## Practical Application
[How this knowledge can be applied in real scenarios]

## Related Concepts
- [Link to related concept 1]
- [Link to related concept 2]

## Questions & Limitations
[Open questions or limitations of this knowledge]
```

### 4. Source-Specific Extraction Guidance

Keep the main skill class-level. When a source family needs narrow guidance, put those notes in `references/` rather than expanding `SKILL.md` with one-session examples.

For technical video examples such as Docker concepts, Proxmox AI server setup, and local AI server/Open WebUI walkthroughs, see `references/topic-specific-video-guidelines.md`. Adapt those examples to the current source instead of forcing every extraction into those categories.

For server/workstation/GPU-host procurement research that must produce durable markdown with multiple bill-of-materials options, used/new purchase links, local operating-cost considerations, and explicit budget/use-case alignment, see `references/hardware-bom-research-and-procurement.md`.

For recruiter-style sourcing or public LinkedIn candidate discovery, see `references/public-linkedin-people-sourcing.md` for a verification-first workflow that treats search snippets as leads, uses browser/web paths early when authwalls appear, and avoids padding counts with unverified matches.

### 5. Documentation Standards

All extracted knowledge should be stored in the `knowledge_extracted` repository with:

- **File Naming**: `{topic}-{specific-concept}.md` (e.g., `docker-container-lifecycle.md`)
- **Frontmatter**: Include metadata for organization
- **Tagging**: Use consistent tags for cross-referencing
- **Linking**: Use relative links to connect related concepts
- **Versioning**: Commit regularly with descriptive messages

### 6. Quality Assurance

Before committing extracted knowledge:
- [ ] Verify technical accuracy against source
- [ ] Check for completeness of explanation
- [ ] Ensure proper attribution and timestamps
- [ ] Validate any code snippets or commands
- [ ] Confirm formatting matches repository standards
- [ ] Check for duplicate or overlapping content

### 7. Repository Management

Use the github-repo-management skill to:
- Clone/create the knowledge_extracted repository
- Create feature branches for extraction sessions
- Commit extracted knowledge files
- Push changes to remote
- Create pull requests for review (if applicable)

**Deliver links, not just a summary.** When work lands in a GitHub repo, Jordan's standing expectation is a final reply containing a hyperlink to each created markdown file (use the `/blob/main/<path>` form from the pushed branch), plus the batch index if one exists — he asked for this explicitly ("when you finish, please provide a hyperlink to the three markdown files you create in the GitHub repository"). Don't make him hunt for the files.

If GitHub authentication is unavailable at push time, do **not** discard or leave unstaged work: validate artifacts, commit locally on the bot branch, attempt the push once, then report the exact auth blocker and the `git push origin <branch>` command for the user to run after credentials are restored.

### 8. Attachment-Based Research Packages

When the user supplies a prompt/document plus an archive and asks for researched markdown answers in a repository, follow `references/attachment-research-package-workflow.md`: extract to `/tmp`, inspect inventory/headings, redact secrets before committing, split broad research into durable topic files, include a sources/caveats file, run a simple secret scan, then commit/push on the correct branch.

## Pitfalls & How to Avoid Them

1. **Loss of Context**: Always include timestamps and source references
   - Solution: Extract with timestamps immediately when reviewing

2. **Over-extraction**: Getting too granular and losing the forest for the trees
   - Solution: Focus on concepts that are reusable and actionable

3. **Under-extraction**: Missing important nuances or prerequisites
   - Solution: Review extraction against source multiple times

4. **Inconsistent Formatting**: Different styles making knowledge hard to consume
   - Solution: Use templates and linting tools

5. **Attribution Errors**: Failing to properly credit sources
   - Solution: Capture source info before starting extraction

6. **Knowledge Silos**: Extracting without connecting to existing knowledge
   - Solution: Always search for related concepts before finalizing

7. **Candidate-profile overclaiming**: Treating search-engine snippets or inaccessible LinkedIn pages as if they were fully verified profiles
   - Solution: Use snippets only as lead generation, corroborate with accessible public evidence, and label confidence/caveats explicitly

8. **Getting stuck in terminal-only sourcing**: Repeating shell-based search/fetch attempts after bot checks or authwalls are obvious
   - Solution: Escalate early to browser/web-capable tooling or subagents and return the verified count instead of padding results

## Templates and References

See the `references/` directory for:
- `video-extraction-plan.md` — generic single-video and batch-video extraction plan, including YouTube knowledge-repo artifact expectations
- `deepapi-transcript-extraction.md` — DeepAPI `/v1/scrape/youtube/transcript` workflow: auth from `~/.deepapi/env`, required `Idempotency-Key` header, float-`startSecs` timestamp handling, artifact naming, and a proven script skeleton
- `attachment-research-package-workflow.md` — workflow for prompt/archive research packages, secret redaction, parallel research, and Git-backed markdown deliverables
- `hardware-bom-research-and-procurement.md` — server/workstation/GPU-host BOM research pattern: use-case-first analysis, existing-parts handling, eBay/new sourcing mix, power-cost framing, and local-commit/push-blocker reporting
- `public-linkedin-people-sourcing.md` — verification-first workflow for LinkedIn/public-profile candidate sourcing, including confidence labels, caveats, and early escalation from shell search to browser/web tooling when needed
- Video-specific extraction guides
- Quality checklists
- Formatting standards
- Example extractions

See the `templates/` directory for:
- Markdown templates for different content types
- Frontmatter examples
- Linking conventions

See the `scripts/` directory for:
- Automated extraction helpers
- Validation scripts
- Repository maintenance tools