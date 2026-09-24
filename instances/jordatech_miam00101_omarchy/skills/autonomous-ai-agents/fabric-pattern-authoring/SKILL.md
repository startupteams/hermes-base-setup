---
name: fabric-pattern-authoring
description: "Author and manage Fabric patterns — modular prompt templates for AI augmentation organized by real-world task. Create, collect, and organize reusable AI solutions."
version: 1.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [fabric, patterns, prompts, augmentation, task-templates]
    related_skills: [armory, openharness, nomos]
---

# Fabric Pattern Authoring

> **Fabric** — Open-source framework for augmenting humans using AI. Modular system for solving specific problems using crowdsourced AI prompts that can be used anywhere.

**Source:** `github.com/startupteams/Fabric`
**Language:** Go

## When to Use

- **Creating prompt templates** for repeatable AI tasks (summarization, extraction, analysis)
- **Organizing prompts** by real-world task type
- **Building prompt libraries** for team-wide use
- **Customizing AI behavior** through structured prompt templates
- **Integrating Fabric prompts** into Claude Code, terminal workflows, or API calls

## Architecture

Fabric organizes prompts by task category:

```
fabric/
├── patterns/                    # Reusable prompt templates
│   ├── summarization/
│   │   ├── blog-post.md
│   │   ├── article.md
│   │   └── meeting-notes.md
│   ├── extraction/
│   │   ├── entity-extractor.md
│   │   └── sentiment-analysis.md
│   ├── classification/
│   │   ├── spam-detector.md
│   │   └── intent-classifier.md
│   ├── generation/
│   │   ├── blog-post.md
│   │   └── tweet.md
│   ├── analysis/
│   │   ├── competitive-analysis.md
│   │   └── code-review.md
│   └── ...                    # More categories
├── contexts/                   # System prompt templates
│   ├── summarizer.context
│   ├── extractor.context
│   └── classifier.context
├── docs/                       # Documentation
└── fabric                      # CLI binary
```

## Installing Fabric

```bash
# Via go
go install github.com/danielmiessler/fabric/fabric@latest

# Via binary (recommended)
curl -fsSL https://get.fabric.com | bash

# Via package manager
brew install fabric
```

## Pattern Structure

Each Fabric pattern is a markdown file with frontmatter:

```markdown
# Pattern: Blog Post Summarizer

## Context
You are an expert blog post summarizer. You can distill complex articles into clear, concise summaries.

## Instructions
1. Read the input text
2. Identify key arguments and evidence
3. Extract 3-5 main points
4. Write a summary in plain English
5. Include a one-sentence takeaway

## Input Format
- Article text or URL

## Output Format
- Title
- 3-5 bullet points
- One-sentence takeaway

## Example
Input: "Long article text..."
Output:
### Title: ...
- Key point 1
- Key point 2
- Key point 3

**Takeaway:** ...
```

## Using Fabric Patterns

### CLI Usage

```bash
# Summarize a URL
fabric sum -u https://example.com/article

# Summarize from stdin
cat article.md | fabric sum

# Extract entities
echo "Apple Inc. was founded by Steve Jobs in Cupertino" | fabric extract -t entity

# Classify text
echo "This email is important" | fabric classify

# Generate content
fabric generate -t blog-post --prompt "AI agent frameworks comparison"

# Search patterns
fabric search "summarize"
```

### Programmatic Usage

```bash
# Use a specific pattern
fabric run pattern-name -i "input text"

# Pipe file content
cat file.txt | fabric run pattern-name

# Custom context
fabric run pattern-name -c custom-context.txt -i "input"
```

## Creating Custom Patterns

### Step 1: Create the Pattern File

```bash
mkdir -p ~/.fabric/patterns/my-category
cat > ~/.fabric/patterns/my-category/my-pattern.md << 'EOF'
# Pattern: My Custom Pattern

## Context
[What the AI should know about its role]

## Instructions
[Step-by-step instructions]

## Input Format
[What input the pattern expects]

## Output Format
[Expected output structure]

## Example
[Input/Output example]
EOF
```

### Step 2: Organize by Category

```
~/.fabric/patterns/
├── my-category/
│   ├── my-pattern.md
│   └── another-pattern.md
├── summarization/
├── extraction/
└── ...
```

### Step 3: Test the Pattern

```bash
# Test with sample input
echo "Sample input text" | fabric run my-pattern

# Test with file
cat test-file.txt | fabric run my-pattern

# Test with URL
fabric run my-pattern -u https://example.com
```

## Context Templates

Fabric uses context templates for consistent system prompts:

```bash
# Create a context
cat > ~/.fabric/contexts/custom-summarizer.context << 'EOF'
You are a professional summarizer with expertise in:
- Technical content
- Business documents
- Research papers

Your summaries are:
- Accurate
- Concise
- Actionable
- Well-structured
EOF

# Use the context
fabric run pattern-name -c ~/.fabric/contexts/custom-summarizer.context
```

## Rest API Server

Fabric includes a REST API server for programmatic access:

```bash
# Start the API server
fabric serve --port 8080

# API endpoints
curl -X POST http://localhost:8080/api/v1/summarize \
  -d '{"url": "https://example.com/article"}'

curl -X POST http://localhost:8080/api/v1/extract \
  -d '{"text": "Extract entities from this text", "type": "entity"}'

curl -X GET http://localhost:8080/api/v1/patterns
curl -X GET http://localhost:8080/api/v1/patterns?category=summarization
```

## Integration with Other Tools

### Fabric + Claude Code

```bash
# Use Fabric patterns inside Claude Code
fabric run summarizer -u https://example.com | claude -p "Based on this summary, draft a blog post"

# Pipe multiple patterns together
fabric extract -t entity -i "Raw text" | fabric analyze -t entity-analysis
```

### Fabric + Hermes

```bash
# Use Fabric patterns in Hermes terminal commands
terminal(command='cat article.txt | fabric run my-summarizer')

# Create a Hermes skill wrapper for common Fabric patterns
```

### Fabric + NOMOS

```yaml
# Use Fabric as a tool in NOMOS workflows
steps:
  - name: summarize
    tool: fabric_run
    config:
      pattern: "summarizer"
      input: "{{ step.fetch.content }}"
```

### Fabric + Armory

```bash
# Armory skills can reference Fabric patterns
# In a SKILL.md:
# When asked to summarize content:
# 1. Run `fabric run summarizer -i "${content}"`
# 2. Present the result to the user
```

## Pitfalls & Gotchas

1. **Patterns are plain markdown** — They're not code. Test them with real input before deploying.
2. **Context overrides system prompt** — The `-c` flag replaces, not appends to the system prompt. Be explicit.
3. **Pattern search is fuzzy** — `fabric search` uses fuzzy matching, not exact. Use specific terms.
4. **API server needs explicit start** — `fabric serve` doesn't auto-start. Run it in background for persistent access.
5. **Patterns are user-local by default** — They live in `~/.fabric/`. Share with teams via version control or network paths.
6. **No pattern versioning** — Fabric doesn't track pattern versions. Use git or your own versioning system.
7. **CLI exit codes are generic** — Most commands return 0 on success, 1 on failure. No detailed error codes.
8. **Rest API is basic** — The API server is functional but minimal. For complex integrations, use the CLI programmatically.

## Quick Start

```bash
# 1. Install
curl -fsSL https://get.fabric.com | bash

# 2. Try built-in patterns
echo "Long text here" | fabric sum
fabric search "analyze"

# 3. Create a custom pattern
mkdir -p ~/.fabric/patterns/my-stuff
cat > ~/.fabric/patterns/my-stuff/code-review.md << 'EOF'
# Pattern: Code Review

## Context
You are a senior software engineer reviewing code.

## Instructions
1. Read the code carefully
2. Check for: bugs, security issues, performance, style
3. Report findings with file:line references
4. Suggest fixes

## Output Format
### Issues Found:
1. [file:line] Issue description → Suggested fix

### Overall Assessment:
- [ ] No issues
- [ ] Minor issues (fix in next PR)
- [ ] Major issues (block merge)
EOF

# 4. Use it
git diff HEAD~1 | fabric run code-review
```

## Related Skills

- `armory` — Armory provides production-grade skills; Fabric provides the pattern framework they're built on
- `openharness` — OpenHarness can load Fabric patterns as part of its skill system
- `nomos` — NOMOS workflows can invoke Fabric patterns as tools
- `hermes-agent` — Hermes can wrap Fabric CLI commands as skills
