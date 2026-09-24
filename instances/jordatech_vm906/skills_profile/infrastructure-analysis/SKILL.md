---
name: infrastructure-analysis
description: Write structured technical infrastructure analysis documents — server capacity planning, GPU/CPU budgeting, networking topology, Proxmox VM architecture, and hardware cost/benefit reviews.
---

# Infrastructure Analysis

Write structured technical analysis documents for hardware, networking, and infrastructure decisions. Target audience: systems engineers + network engineers reviewing architecture proposals.

## Trigger Conditions

- User asks for server capacity/cost analysis
- Hardware purchasing review with quantitative trade-offs
- Proxmox/virtualization architecture planning
- Proxmox cluster provisioning or operational changes, including LXC/VM deployment through the Proxmox API when SSH is unavailable
- vLLM / llama-server / inference engine deployment plans
- Network topology or power budget analysis
- Multi-GPU or multi-node cluster design

## Pre-Analysis: Conflict Detection

**BEFORE** producing any analysis or diagrams, scan ALL documentation files in the project for conflicting specs:

1. Compare GPU configs across docs (e.g., RTX 3080 Turbo 20GB vs RTX 5060 Ti 16GB)
2. Compare RAM per server across docs
3. Compare networking topology claims (single switch vs. dual-switch vs. DAC mesh)
4. Compare power budget numbers
5. **Flag every contradiction explicitly** — produce a "⚠️ CONFLICTING SPECS" section before any recommendation
6. Choose ONE configuration as the source of truth (usually the one with more VRAM/more production validation)
7. Document which doc is superseded and why

If no contradictions exist, skip this section and proceed to the core analysis.

### Then verify the load-bearing claims against the LIVE system (not just the docs)

Documents — including plans the user hands you — describe *intent*. Before producing an analysis or
executing a plan, confirm the few facts the whole thing rests on by probing the running system:

1. List the actors' real current state (`/v1/models`, `systemctl show -p ExecStart`, VM configs).
2. Confirm every "existing / already working" asset **actually exists and is what it is claimed to be**.
   A name is not evidence: a model registered as `<x>-api` is provider-backed, not local; a response
   carrying a `provider:` field or a `gen-…` id is cloud. Verify with the artefacts, not the label.
3. Re-measure the hardware envelope (`free -g` inside the guest, `nvidia-smi`, Proxmox `memory`/`balloon`)
   rather than trusting a table in the plan.
4. Record discrepancies in a table, then **stop and report** if a discrepancy makes the plan's premise
   false — do not "fix" the plan silently by substituting a different model, host, or engine.

### Executing a plan: honor its own stop conditions

When the deliverable is *execution* of a written plan, the plan's stop conditions are binding, and a
blocked-with-evidence outcome is a **success**, not a failure. Checklist:

- Do the non-destructive, gated work first (baseline capture, rollback artefacts) — it is
  unconditional and never wasted.
- Do the feasibility/fit gateway **before** any download, service stop, or config change.
- Map every blocker to the plan's own numbered stop condition, so the report speaks its language.
- Never relabel, substitute, or partially deploy to manufacture a "done".
- Preserve rollback state by *not changing* what you did not have to change; state that explicitly in
  the report ("no production change; nothing to roll back").
- Still do the parts that are unblocked and independent — and say which they are.

## Output Format (Required)

Every infrastructure analysis MUST follow this structure:

```markdown
# <Title>
## <Date + Prepared by>

## 1. <Core Analysis Section 1 — numeric/computational>
## 2. <Section 2 — configuration evaluation>
## 3. <Section 3 — architecture recommendation>
## 4. <Section 4 — hybrid/best-of-both>
## 5. <Summary table or decision matrix>

## N. Key Takeaways
### ✅ DO
### ❌ DON'T

## Appendix A/B/C: <Reference, syntax, fix recipes>
```

### Specific requirements:
- **Quantitative tables everywhere** — no prose where a table works. Use pipe-tables with ✅/⚠️/❌ verdicts
- **Bash code blocks** for every config recommendation — include full commands, not snippets
- **Per-server breakdown** — if analyzing multi-node clusters, create a row per server node with CPU, RAM, GPUs, config, cores used, free cores, verdict
- **Decision matrix** — end with a summary table mapping server → CPU → inference type → cores → headroom → verdict
- **Appendices** — include at least one appendix with syntax reference or fix recipes

## Pitfalls

### CRITICAL: Never overwrite binary files
- **NEVER** use `write_file()` on a path ending in `.pdf`, `.xlsx`, `.csv`, `.png`, `.jpg`, or other binary extensions
- **NEVER** use `write_file()` to "update" a file you haven't read first to verify its type
- **ALWAYS** check file type with `file` command or inspect bytes before writing text content
- If you need to write analysis content, use `.md` extension and verify the target path is correct
- **SAFETY CHECK:** Before any `write_file` call, verify: `file <path>` returns "text" not "PDF", "Excel", etc.

### Technical pitfalls
- When doing Proxmox cluster operations, start with API discovery (`/nodes`, `/cluster/resources`, target node status/storage, existing LXC configs) before creating or modifying resources.
- Proxmox credentials are realm-sensitive: verify `/access/domains` and use the exact realm suffix (for example `@LLDAP-Domain`), not guessed shortcuts like `@ldap`.
- Proxmox UI/API permissions do not imply SSH/root shell access; if SSH is unavailable, prefer supported PVE API operations plus first-boot LXC configuration over forcing host shell access.
- When deleting Proxmox resources through the API, pass DELETE options as query parameters; some endpoints reject request bodies with `Unexpected content`.
- When polling Proxmox tasks, extract the node from the returned UPID and poll that node's `/tasks/<upid>/status`; uploads and proxied operations may report a different task node than the target resource.
- When analyzing vLLM CPU budget: use `2 + N` formula (API server + engine core + GPU workers)
- When analyzing llama-server: `--threads` value must be ≤ VM vCPU count, not host physical core count
- When analyzing MoE models: `--override-tensor "exps=CPU"` shifts routed expert FFN to RAM, which is CPU-bound decode
- NUMA pinning matters: Threadripper Pro is dual-socket; vLLM workers lose ~15% performance if cross-socket
- Never split multi-GPU TP/EP across Proxmox VMs — keep all GPUs for one model in one VM

## Architecture Diagrams (Required for multi-tier designs)

Every multi-tier infrastructure analysis MUST include Mermaid-compatible diagrams in a dedicated file (`architecture.md` in the same research directory). These diagrams are:

- **Renderable in GitHub** — no external tooling needed
- **Version-controllable** — plain text, diff-friendly
- **Editable** — simple to update when hardware changes
- **Readable** — clear tier separation, explicit connections

Include AT MINIMUM:
1. **Full cluster overview** — all tiers, network, power, data flow
2. **Data/request flow** — sequence diagram showing how an agent request travels through the stack
3. **Build detail** — single-server deep-dive showing CPU, GPU, PSU, cooling, interconnect

Include when relevant:
4. **Proxmox/virtualization cluster** — node roles, HA groups, storage layout
5. **Network topology** — switch hierarchy, VLAN plan, cable types
6. **Power budget** — per-device wattage, circuit planning, UPS/PDU placement
7. **Build timeline** — gantt chart showing priority order and dependencies

Mermaid syntax reference:
- `graph TB` / `graph LR` — general flowcharts
- `sequenceDiagram` — request/response flows
- `gantt` — build timelines
- `subgraph` — tier/zone grouping
- `classDef` / `class` — color coding by component type

Template: see `templates/mermaid-architecture.md`

## Templates

See `templates/mermaid-architecture.md` for a ready-to-fill Mermaid diagram template with all diagrams pre-created.

## References

See `references/` for:
- `references/proxmox-pdm-lxc-provisioning.md` — PDM-on-Proxmox LXC provisioning via the Proxmox API, including community-script install mechanics, LLDAP verification, UPID polling, and API-only workarounds when SSH is unavailable.
- Hardware purchasing records from analysis sessions
- GPU spec sheets and benchmark data
- Proxmox VM passthrough configurations

Related: `marion-vllm-bench-ops` carries the fleet-specific counterpart — measured hardware envelope,
pre-flight model feasibility gate, provider-vs-local detection, and a read-only
`scripts/fleet_probe.py` that produces the live baseline a plan review depends on.
