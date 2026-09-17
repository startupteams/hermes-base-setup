---
name: nomos
description: "Structured LLM-powered assistant framework — configurable flows, state machines, tool chaining, and multi-step workflows from no-code to full-code. Ships with CLI, Python SDK, TypeScript SDK, and Docker."
version: 1.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [nomos, workflow, state-machine, flows, tools, cli, python, typescript]
    related_skills: [ruflo, openharness, armory, openspec]
---

# NOMOS — Structured Agent Workflows

> **NOMOS** is a framework for building advanced LLM-powered assistants with structured, multi-step workflows. Configurable flows, tools, and integrations — making complex agent development accessible from no-code to full-code.

**Source:** `github.com/startupteams/nomos`
**Packages:** `pip install nomos[cli]`, `npm install nomos-sdk`

## When to Use

- Building **multi-step agent workflows** with explicit state management
- Chaining **tools across steps** (e.g., scrape → analyze → summarize → save)
- Creating **reusable agent templates** with defined inputs and outputs
- Managing **long-running agent sessions** with checkpoint/restore
- Prototyping **no-code workflows** → YAML → full Python implementation
- Deploying agents with **built-in session management and rate limiting**

## Key Features

| Feature | Description |
|---------|-------------|
| **State Machines** | Explicit workflow states with transitions and guards |
| **Tool Chaining** | Connect tools across steps with data passing |
| **Session Management** | Persistent sessions with checkpoint/restore |
| **Rate Limiting** | Built-in rate limiting and retry logic |
| **Security** | CSRF protection, input validation, tool sanitization |
| **Multi-Platform** | CLI, Python SDK, TypeScript SDK, Docker |
| **Playground** | No-code drag-and-drop agent creation |

## Architecture

```
┌─────────────────────────────────────────────┐
│              NOMOS Agent                     │
├─────────────────────────────────────────────┤
│  Flow Engine (State Machine)                │
│  ┌────────┐    ┌────────┐    ┌────────┐   │
│  │  Start │───▶│  Step1 │───▶│  Step2 │──▶│
│  └────────┘    └────────┘    └────────┘   │
│       │              │              │       │
│       ▼              ▼              ▼       │
│  [Guard]        [Guard]        [Guard]     │
│                                              │
│  Tool Registry                                │
│  ┌────────┐ ┌────────┐ ┌────────┐          │
│  │ Tool A │ │ Tool B │ │ Tool C │          │
│  └────┬───┘ └────┬───┘ └────┬───┘          │
│       └──────────┼──────────┘               │
│                  ▼                           │
│          Session Manager                    │
│     (Checkpoints, Rate Limits, History)     │
└─────────────────────────────────────────────┘
```

## Installation

```bash
# Python (with CLI)
pip install nomos[cli]

# TypeScript SDK
npm install nomos-sdk

# Docker
docker pull ghcr.io/dowhiledev/nomos:latest

# Playground
# https://nomos-builder.vercel.app/ — drag-and-drop agent creation
```

## Defining Workflows

### Python (Full-Code Approach)

```python
from nomos import Agent, Flow, Step, Action, Route

# Define a research workflow
research_agent = Agent(
    name="research-analyst",
    description="Research and summarize topics"
)

# Define steps
step1 = Step(
    name="search",
    tool="web_search",
    config={"query": "{{ user_query }}"}
)

step2 = Step(
    name="summarize",
    tool="llm_summarize",
    config={"source": "{{ step1.results }}"}
)

step3 = Step(
    name="save",
    tool="file_write",
    config={"path": "research/{{ user_query_slug }}.md", "content": "{{ step2.summary }}"}
)

# Create flow with routing
flow = Flow(
    name="research-flow",
    steps=[step1, step2, step3],
    routes=[
        Route(
            from="search",
            condition="step1.results.length > 0",
            to="summarize"
        ),
        Route(
            from="search",
            condition="step1.results.length == 0",
            to="error_handler"
        )
    ]
)

# Run the agent
result = research_agent.run(flow, inputs={"user_query": "AI agent frameworks 2024"})
```

### YAML (Intermediate Approach)

```yaml
# nomos-flow.yaml
agent:
  name: data-pipeline
  description: Ingest, transform, and export data

flows:
  - name: daily-report
    steps:
      - name: fetch-data
        tool: web_fetch
        config:
          url: "{{ api_endpoint }}"
        outputs:
          - raw_data

      - name: transform
        tool: python_transform
        config:
          script: |
            data = {{ step.fetch-data.raw_data }}
            return transform(data)
        outputs:
          - cleaned_data

      - name: export
        tool: file_write
        config:
          path: reports/daily-{{ timestamp }}.csv
          content: "{{ step.transform.cleaned_data }}"
```

### No-Code (Playground)

1. Visit https://nomos-builder.vercel.app/
2. Drag tools onto the canvas
3. Connect them with routes
4. Export to YAML or Python
5. Deploy with NOMOS CLI

## State Machine Pattern

NOMOS uses explicit state machines for reliable workflow execution:

```python
from nomos.state_machine import StateMachine, Transition

# Define states
states = {
    "idle": {"description": "Waiting for input"},
    "processing": {"description": "Currently processing"},
    "waiting_human": {"description": "Awaiting human approval"},
    "error": {"description": "Error state — requires manual intervention"},
    "complete": {"description": "Workflow complete"}
}

# Define transitions
transitions = [
    Transition(from_state="idle", to_state="processing", guard="has_input"),
    Transition(from_state="processing", to_state="waiting_human", guard="needs_approval"),
    Transition(from_state="processing", to_state="complete", guard="no_approval_needed"),
    Transition(from_state="waiting_human", to_state="processing", guard="approved"),
    Transition(from_state="waiting_human", to_state="error", guard="rejected"),
    Transition(from_state="*", to_state="error", guard="any_error"),  # * = any state
]

sm = StateMachine(initial_state="idle", states=states, transitions=transitions)

# Execute transitions
sm.transition("processing")  # Move to processing
sm.transition("complete")    # Complete the workflow
```

## Tool Integration

NOMOS supports multiple tool types:

| Tool Type | Examples | Integration |
|-----------|----------|-------------|
| **Python Functions** | Custom logic | `@nomos.tool("my_tool")` decorator |
| **CrewAI Tools** | Multi-agent tools | Direct import from crewai |
| **LangChain Tools** | LangChain ecosystem | Direct import from langchain |
| **External APIs** | REST endpoints | HTTP tool with auth config |
| **NOMOS Built-in** | web_fetch, file_write, python_transform | Ready-to-use |

```python
# Register custom tool
import nomos

@nomos.tool("data_validator")
def validate_data(data: dict, schema: str) -> dict:
    """Validate data against a schema."""
    # Validation logic
    return {"valid": True, "errors": []}

# Use in a step
step = Step(
    name="validate",
    tool="data_validator",
    config={"data": "{{ input_data }}", "schema": "user_profile"}
)
```

## Session Management

```python
from nomos import Session

# Create a session
session = Session.create(agent="research-analyst", id="session-001")

# Run with checkpoint
result = session.run(
    flow="research-flow",
    inputs={"query": "AI trends"},
    checkpoint_every="every_step"  # Save state after each step
)

# Resume from checkpoint
session.restore("session-001")
result = session.continue_from("step-3")

# List sessions
Session.list()  # All sessions for this agent
```

## Rate Limiting & Retries

```python
from nomos import RateLimiter, RetryPolicy

# Rate limiter
limiter = RateLimiter(
    requests_per_minute=60,
    burst_size=10
)

# Retry policy
retry = RetryPolicy(
    max_retries=3,
    backoff_factor=2,  # 1s, 2s, 4s
    retryable_errors=["rate_limit", "timeout", "connection_error"]
)

# Apply to agent
agent = Agent(
    name="safe-agent",
    rate_limiter=limiter,
    retry_policy=retry
)
```

## Security Features

| Feature | Description |
|---------|-------------|
| **CSRF Protection** | Built-in CSRF tokens for web-facing agents |
| **Input Validation** | Schema validation on all tool inputs |
| **Tool Sanitization** | Automatic sanitization of tool parameters |
| **Session Isolation** | Each session has isolated state and tools |
| **Audit Logging** | Full audit trail of all agent actions |

```python
# Enable security
agent = Agent(
    name="secure-agent",
    security={
        "csrf_protection": True,
        "input_validation": True,
        "tool_sanitization": True,
        "audit_logging": True
    }
)
```

## Docker Deployment

```dockerfile
FROM ghcr.io/dowhiledev/nomos:latest

# Copy your flows
COPY flows/ /app/flows/
COPY config.yaml /app/config.yaml

# Run the agent server
CMD ["nomos", "serve", "--port", "8000"]
```

```bash
# Start NOMOS server
docker run -p 8000:8000 \
  -v $(pwd)/flows:/app/flows \
  ghcr.io/dowhiledev/nomos:latest

# API endpoints
curl http://localhost:8000/agents/my-agent/run \
  -d '{"flow": "research-flow", "inputs": {"query": "AI trends"}}'
```

## CLI Commands

```bash
# Create a new agent
nomos init my-agent --template research

# Run an agent locally
nomos run my-agent --flow research-flow --input "query=AI trends"

# Start the agent server
nomos serve --port 8000 --workers 4

# List agents
nomos agents list

# Export agent config
nomos export my-agent --format yaml

# Validate flow
nomos validate flows/research.yaml
```

## Playground Integration

The no-code playground exports to multiple formats:

```bash
# Export playground design to YAML
nomos playground export --input design.json --format yaml --output flow.yaml

# Export to Python
nomos playground export --input design.json --format python --output agent.py

# Sync playground with local files
nomos playground sync --dir ./flows
```

## Pitfalls & Gotchas

1. **State machines are explicit** — Define all states and transitions before running. Missing transitions cause silent failures.
2. **Tool outputs must be serializable** — If a tool returns a complex object, convert to dict/list before passing to next step.
3. **Rate limiting applies per-agent** — If you have multiple agents, each has its own rate limiter. Configure per-agent.
4. **Checkpoints add latency** — `checkpoint_every="every_step"` slows execution. Use `checkpoint_every="critical_step"` for performance.
5. **Playground exports are incomplete** — The playground generates YAML/Python templates but may need manual adjustment for complex logic.
6. **Docker requires API key** — The Docker image needs NOMOS_API_KEY or external provider keys in the environment.
7. **Session history grows** — Long-running sessions accumulate history. Use `Session.purge()` to clean old entries.
8. **TypeScript SDK has different API** — The Python and TypeScript SDKs are similar but not identical. Check the TS docs for differences.

## Quick Start

```python
# 1. Install
pip install nomos[cli]

# 2. Create an agent
nomos init web-researcher --template research

# 3. Define a simple flow
from nomos import Agent, Flow, Step

agent = Agent(name="web-researcher")

flow = Flow(
    name="simple-research",
    steps=[
        Step(name="search", tool="web_search", config={"query": "{{ query }}"}),
        Step(name="summarize", tool="llm_summarize", config={"source": "{{ step.search.results }}"}),
    ]
)

# 4. Run
result = agent.run(flow, inputs={"query": "best practices for AI agents"})
print(result.steps["summarize"].output)
```

## Related Skills

- `ruflo` — Ruflo orchestrates NOMOS agents as part of a swarm
- `openharness` — OpenHarness provides the workspace for NOMOS sessions
- `armory` — Armory provides pre-built tools that NOMOS can use
- `openspec` — OpenSpec defines specs that NOMOS workflows implement
- `hermes-agent` — Hermes can spawn NOMOS agents via terminal or delegation
