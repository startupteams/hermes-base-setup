# Dataset bounty demand signals

Use this reference when enriching a data-marketplace, data-collection, or AI-training-data business idea with real market/source intelligence.

## When to use

Use when the user asks for dataset bounties, paid data collection links, active recruitment programs, contributor marketplaces, AI training task boards, or proof that buyers/vendors are actively sourcing specific datasets.

## Pattern

1. Treat bounty boards as **source intelligence, not validation**. They show active demand or supply operations, but not that the user's specific business will win buyers.
2. Prefer specific active opportunity pages over generic company homepages.
3. For each link, capture:
   - Organization and linked heading.
   - Dataset/task requirements: modality, contributor type, geography/device/session constraints, quality or metadata needs.
   - Business-model lesson for the user's idea: what this implies for bounties, trust, QA, pricing, or supply acquisition.
4. Add links to the idea frontmatter `source_urls` and add a readable body section near the top, before long scoring/analysis sections.
5. If the idea has leftover generic placeholders, clean them while editing the specific brief: data moat, unit economics, skeptical investor FAQ, and AI necessity answers should all reference the actual dataset, buyer, provenance, and margin model.
6. Sync the source Markdown into the viewer fallback snapshot, validate JSON, build, commit/push both repos, deploy, and verify Basic Auth-protected production safely.

## Example sources used for Common Sense - Dataset Collector

- Defined.ai Partnership Programs / Active Opportunities — M365 productivity data, proprietary codebases with metadata, robotics video/sensor data, produced video, and channel-separated conversational audio.
- DataForce by TransPerfect projects — speech/photo/audio/user-study/annotation/evaluation projects.
- OneForma jobs and named projects — video data collection, native-speaker audio studies, annotation, transcription, judging, prompt authoring.
- Appen/CrowdGen — remote AI data work including audio, voice recording, translation/social/search/ad evaluation, and transcription.
- RWS TrainAI — freelance data creation, annotation, linguistic tasks, and evaluation.
- Outlier, Alignerr, DataAnnotation, Mercor, Mindrift — expert-generated or expert-evaluated AI training data across coding, STEM, legal, finance, medical, language, and reasoning tasks.
- Toloka, Clickworker, Neevo, LXT Crowd — paid microtasks, recordings, photo/video/text/audio/image data collection, annotation, and QA.

## Common Sense-specific lesson

For permissioned mobile-sensor datasets, differentiate from generic crowd/task marketplaces through:

- consent/provenance receipts
- device metadata and sensor schema
- geography/environment labels
- buyer-ready dataset cards
- quality/fraud scoring
- participant trust, deletion, and withdrawal flows
- repeatable bounty templates and acceptance criteria
