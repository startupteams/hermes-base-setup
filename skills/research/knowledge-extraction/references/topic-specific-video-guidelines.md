# Topic-Specific Video Extraction Guidelines

These notes are session-specific examples of how to scope extraction from technical educational videos. Treat them as examples to adapt, not required sections for every extraction.

## Docker Concepts Video

- Focus on containerization principles.
- Capture Docker architecture: daemon, client, registry.
- Clarify image vs. container distinctions.
- Include basic Docker commands such as run, build, push, and pull when the source covers them.
- Summarize volume management basics.
- Summarize networking fundamentals.

## Proxmox AI Server Setup

- Capture Proxmox VE installation basics only insofar as the source explains them.
- Distinguish VM vs. LXC container considerations for AI workloads.
- Extract GPU passthrough configuration steps and warnings.
- Note storage optimization guidance for ML datasets.
- Note network configuration steps for external access.
- Capture resource-allocation heuristics and caveats.

## Local AI Server with Open WebUI

- Extract Open WebUI installation and configuration steps.
- Identify model-serving backends discussed, such as Ollama, llama.cpp, or compatible API servers.
- Capture API integration patterns.
- Capture user-authentication and access-control considerations.
- Summarize performance optimization techniques.
- Note monitoring and logging setup guidance.

## Generalization Rule

When a future source is not one of the examples above, do not force it into these categories. Instead:

1. Identify the system or workflow the source teaches.
2. Extract the reusable primitives, commands, decisions, and pitfalls.
3. Preserve source-specific commands with attribution and timestamps.
4. Move overly narrow examples into a reference file rather than expanding the main SKILL.md.