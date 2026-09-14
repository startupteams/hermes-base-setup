---
title: Architecture Diagram Template
purpose: Starting point for agent infrastructure architecture diagrams
usage: Copy to <project>/hardware_research/architecture.md and fill in specs
---

# <Project Name> — Server Architecture

> **Date:** YYYY-MM-DD  
> **Author:** <Your Name>  
> **Source:** <repo path to hardware research docs>

---

## ⚠️ CURRENT STATE: Conflict Detection

> [IF CONFLICTS EXIST: List every contradictory spec between docs]
> 
> | Doc | GPU Config | VRAM Total | RAM | Status |
> |-----|-----------|------------|-----|--------|
> | Doc A | ... | ... | ... |
> | Doc B | ... | ... | ... |
> 
> **Chosen configuration:** [Explain which plan wins and why]

---

## DIAGRAM 1: Full Cluster Overview

```mermaid
graph TB
    subgraph TIER1["TIER 1: AI INFERENCE"]
        S1[("Server 1<br/>CPU<br/>GPUs<br/>RAM<br/>vLLM Model")]
        S2[("Server 2<br/>CPU<br/>GPUs<br/>RAM<br/>vLLM Model")]
    end

    subgraph TIER2["TIER 2: ORCHESTRATION"]
        PVE1[("Proxmox Node 1<br/>CPU<br/>RAM<br/>Role")]
        PVE2[("Proxmox Node 2<br/>CPU<br/>RAM<br/>Role")]
        PVE3[("Proxmox Node 3<br/>CPU<br/>RAM<br/>Role")]
    end

    subgraph TIER3["TIER 3: EDGE & MANAGEMENT"]
        EDGE[("Edge Node<br/>Role<br/>Specs")]
        NAS[("NAS<br/>Role<br/>Storage")]
    end

    S1 ---|10GbE| S2
    PVE1 <-->|HA Sync| PVE2
    PVE2 <-->|HA Sync| PVE3
    
    PVE1 -.->|API Gateway| S1
    PVE2 -.->|API Gateway| S2
```

---

## DIAGRAM 2: Data Flow (Agent Request Lifecycle)

```mermaid
sequenceDiagram
    participant Agent as Hermes Agent
    participant Router as LiteLLM Router
    participant Gateway as Nginx API Gateway
    participant S1 as Server 1
    participant S2 as Server 2
    participant API as External API

    Agent->>Router: Agent request + context
    Note over Router: 3-Tier Decision Matrix
    
    alt Local (confidential / cost-shield)
        Router->>Gateway: Route to local
        Gateway->>S1: Load-balance
        S1-->>Gateway: Response
    else API (frontier quality)
        Router->>API: Claude / GPT / OpenRouter
        API-->>Router: Response
    end
    
    Router-->>Agent: Final response
```

---

## DIAGRAM 3: Model Routing Decision Matrix

```mermaid
graph TD
    Start[Agent Request] --> Conf{Is data<br/>confidential?}
    Conf -->|Yes| Local[Run locally<br/>Qwen3.6-35B-A3B]
    Conf -->|No| Quality{Quality tier?}
    Quality -->|Small <8B| FreeTier[Free tier / Groq]
    Quality -->|Medium <20B| OpenRouter[OpenRouter / HF]
    Quality -->|Large| Claude[Direct API<br/>Claude Sonnet 4.6]
    Local --> End[Response]
    FreeTier --> End
    OpenRouter --> End
    Claude --> End
```

---

## DIAGRAM 4: Hardware Build Detail

```mermaid
graph TB
    subgraph SERVER["Server Chassis"]
        CPU[CPU<br/>Model / Cores / TDP]
        GPU1[GPU 1<br/>Model / VRAM]
        GPU2[GPU 2<br/>Model / VRAM]
        GPU3[GPU 3<br/>Model / VRAM]
        GPU4[GPU 4<br/>Model / VRAM]
        RAM[RAM<br/>Type / Capacity]
        PSU[PSU<br/>Wattage / 80+ Rating]
        NIC[Network<br/>10GbE SFP+]
    end
    
    CPU --> Motherboard
    GPU1 --> Motherboard
    GPU2 --> Motherboard
    GPU3 --> Motherboard
    GPU4 --> Motherboard
    RAM --> Motherboard
    PSU --> Motherboard
    NIC --> Motherboard
```

---

## DIAGRAM 5: Proxmox Cluster Configuration

```mermaid
graph TB
    subgraph CLUSTER["Proxmox Cluster"]
        N1[("Node A<br/>IP<br/>Specs<br/>VMs")]
        N2[("Node B<br/>IP<br/>Specs<br/>VMs")]
        N3[("Node C<br/>IP<br/>Specs<br/>VMs")]
    end

    N1 <-->|Corosync HA| N2
    N2 <-->|Corosync HA| N3
    N3 <-->|Corosync HA| N1
```

---

## DIAGRAM 6: Power Budget & Circuit Planning

```mermaid
graph TB
    subgraph CIRCUITS["Circuit Planning"]
        C1[Circuit A<br/>Server 1 + Server 2<br/>Peak: ~1,600W]
        C2[Circuit B<br/>Server 3 + Server 4<br/>Peak: ~1,600W]
    end

    subgraph BACKUP["UPS: APC SMX1000"]
        PROXMX[Proxmox Nodes<br/>~105W]
        SWITCH[Network Switch<br/>~15W]
    end

    subgraph TOTALS["Power Totals"]
        IDLE[Idle: ~1,500W]
        MIXED[Mixed: ~2,800W]
        PEAK[Peak: ~3,900W]
    end

    C1 -.-> TOTALS
    C2 -.-> TOTALS
```

---

## Critical Build Constraints

| # | Constraint | Impact | Mitigation |
|---|-----------|--------|------------|
| 1 | [Constraint name] | [What breaks] | [How to fix] |
| 2 | [Constraint name] | [What breaks] | [How to fix] |
| 3 | [Constraint name] | [What breaks] | [How to fix] |

---

## Build Priority Order

```mermaid
gantt
    title Build Timeline
    dateFormat YYYY-MM-DD
    section CRITICAL
    [Task name]       :crit, t1, YYYY-MM-DD, 5d
    section PRIORITY
    [Task name]       :t2, after t1, 10d
    section WAIT
    [Task name]       :t3, YYYY-MM-DD, 15d
```

---

## Architecture Change Log

| Date | Version | Changes |
|------|---------|---------|
| YYYY-MM-DD | v1.0 | Initial architecture |
