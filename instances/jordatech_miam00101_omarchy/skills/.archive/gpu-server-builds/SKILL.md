---
name: gpu-server-builds
description: "Design and provision multi-GPU servers/workstations for AI/ML workloads with budget constraints."
version: 1.0.0
author: c01entrepreneur_bot
license: MIT
metadata:
  hermes:
    tags: [hardware, gpu, ai-workstations, ml-hardware, server-builds, procurement]
    related_skills: [github-repo-management, knowledge-extraction]
---

# GPU Server Builds

Use this skill when the user asks to:
- Design multi-GPU server/workstation configurations for AI/ML training or inference
- Research current GPU pricing and availability across retailers
- Calculate power requirements, thermal needs, and PSU sizing for GPU-rich systems
- Create Bill of Materials (BOM) with direct purchase links within a budget range
- Compare GPU generations (RTX 40-series vs. 30-series vs. AMD Radeon AI PRO)
- Evaluate new-gen vs. current-gen vs. used market tradeoffs
- Optimize for VRAM capacity, power efficiency, or cost-per-GB
- Size power supplies for mining rigs or open-frame multi-GPU chassis
- Account for PCIe risers, thermal paste, and auxiliary components

## Core Principles

### 0. **Use Case Before Parts List**
Do not start with the most powerful-looking GPU. Start with the actual host job.

Before proposing BOMs, explicitly state:
- **Primary workloads**: inference, fine-tuning, training, rendering, transcoding, agents, or mixed hosting
- **Concurrency target**: how many simultaneous users/jobs/models the box should support
- **Runtime profile**: bursty lab machine vs. 24/7 host
- **Constraints already owned**: chassis, motherboard/CPU platform, RAM, storage, PSU inventory, rack power, noise, and cooling
- **Remaining-parts budget**: only price the components still needed, not the whole server if key parts are already owned
- **Failure tolerance**: whether mixed GPUs, consumer cards, or used cards are acceptable operationally

If the user already owns major parts, treat the task as an **upgrade/remaining-BOM optimization problem**. Separate:
1. **Owned parts**
2. **Parts still required**
3. **Optional parts / future upgrades**

### 1. **VRAM is King for AI/ML**
Prioritize total VRAM capacity over raw compute:
- **LLM fine-tuning**: 12GB minimum per GPU, 24GB+ preferred
- **LLM inference**: 16-24GB per GPU for quantized models
- **Diffusion models**: 12-16GB sufficient for most workloads
- **Multi-GPU training**: Total VRAM across all GPUs matters most

### 2. **Power Supply Redundancy**
For 6+ GPU systems:
- **Calculate peak load**: 6 × GPU_TDP + 150W (system overhead)
- **Add 25-30% headroom**: Never exceed 70-75% PSU capacity
- **Use multiple PSUs**: 2× 1000W for 6 GPUs (167W per GPU average) or 3× 1000W for headroom
- **80+ Platinum/Titanium**: Better efficiency = lower electricity costs + higher MTBF
- **Modular PSUs**: Easier cable management in dense configurations

### 3. **Thermal Management**
- **Open-frame mining rigs**: Excellent airflow, allow 2-slot spacing minimum
- **Ambient temp**: Keep <30°C for optimal component lifespan
- **Fan curves**: 70-80% fan speed at 70°C GPU temp
- **Thermal paste**: Apply quality paste (Arctic MX-6, Noctua NT-H2)

### 4. **PCIe Riser Requirements**
- **8-lane vs. 1-lane**: 8-lane for better GPU-GPU communication
- **Length**: 200-300mm for standard GPUs in mining rigs
- **Type**: PCIe 3.0 x16 (backward compatible with 4.0/5.0 GPUs)
- **Quality**: Cheap risers cause instability under load

### 5. **Purchase Strategy**
- **New current-gen**: RTX 40-series = best balance of efficiency/features
- **Previous-gen**: RTX 30-series = better VRAM/price ratio but less efficient
- **AMD AI PRO**: R9700 (32GB) = maximum VRAM but higher cost
- **RTX 50-series**: Monitor release dates (5060 Ti ~$550, 5070 ~$610 announced)
- **Used market**: 30-40% savings but no warranty, mining history unknown
- **Do not default to Amazon-only procurement**: for budget-constrained builds, include used-market sources such as eBay alongside new retail sources and call out warranty/return tradeoffs.
- **Prefer direct BOM links per configuration**: every full BOM should include direct purchase URLs for GPUs and PSUs, plus a subtotal that reflects the remaining-parts budget only.
- **Call out mixed-GPU consequences**: if reusing an older card (for example a legacy Quadro) could reduce effective cluster performance, complicate drivers, or force weaker fleet-wide settings, say so plainly and recommend excluding it unless it serves a distinct isolated job.

## Budget Tier Guidelines

### **Entry Tier ($2,000-$2,500 for 6 GPUs + PSUs)**
- **GPU**: RTX 4060 Ti 16GB (~$330 each = $1,980)
- **PSU**: 2× 1000W 80+ Gold (~$380)
- **Total VRAM**: 96GB
- **Best for**: LLM fine-tuning (8B models), Stable Diffusion XL, learning

### **Mid Tier ($3,000-$3,500 for 6 GPUs + PSUs)**
- **GPU**: RTX 4070 Ti 12GB (~$700 each = $4,200) → over budget
- **GPU**: RTX 4070 Ti 12GB + RTX 4060 Ti 16GB mix (~$3,800)
- **PSU**: 2× 1000W 80+ Gold (~$380)
- **Total VRAM**: 66-72GB
- **Best for**: Llama-3-70B quantized inference, medium fine-tuning

### **High VRAM Tier ($3,500-$4,000 for 6 GPUs + PSUs)**
- **GPU**: RTX 3090 used (~$800 each = $4,800) → over budget
- **GPU**: RTX 3090 Ti used (~$900 each) → over budget
- **GPU**: Mixed 12GB/16GB optimized (~$3,700)
- **PSU**: 2-3× 1000W 80+ Platinum (~$600)
- **Total VRAM**: 66-144GB (depending on mix)
- **Best for**: Production inference, multi-tenant AI server

### **Enterprise Tier ($10,000+ for 6 GPUs + PSUs)**
- **GPU**: AMD Radeon AI PRO R9700 32GB (~$1,968 each = $11,808)
- **PSU**: 3× 1600W 80+ Titanium (~$1,962)
- **Total VRAM**: 192GB
- **Best for**: Enterprise LLM serving, massive model distribution

## GPU Selection Matrix

| GPU | VRAM | TDP | Price (6x) | Total VRAM | Best Use Case |
|-----|------|-----|------------|------------|---------------|
| RTX 4060 Ti 16GB | 16GB | 280W | $1,980 | 96GB | Budget AI, SDXL |
| RTX 4070 Ti 12GB | 12GB | 285W | $4,200 | 72GB | LLM inference |
| RTX 4080 Super 16GB | 16GB | 320W | $7,560 | 96GB | High-end training |
| RTX 4090 24GB | 24GB | 450W | $19,800 | 144GB | Professional ML |
| RTX 3090 24GB (new) | 24GB | 350W | $8,640 | 144GB | Maximum VRAM (new) |
| RTX 3090 24GB (used) | 24GB | 350W | $4,800 | 144GB | Best VRAM/price |
| RTX 3090 Ti 24GB | 24GB | 450W | $10,800 | 144GB | High-end training |
| AMD R9700 32GB | 32GB | 270W | $11,808 | 192GB | Enterprise ROCm |
| RTX 5060 Ti 16GB (announced) | 16GB | ~200W | $3,300 | 96GB | Future budget build |
| RTX 5070 12GB (announced) | 12GB | ~250W | $3,660 | 72GB | Future mid-tier |

## PSU Sizing Rules

### **Formula**
```
Required PSU Capacity = (GPU_count × max_GPU_TDP) + system_overhead
                       = (6 × 450W) + 150W = 2,850W peak
```

### **Recommendation**
- **6 GPUs @ 300W each**: 2× 1000W PSUs (75% load each)
- **6 GPUs @ 450W each**: 3× 1000W PSUs or 2× 1600W PSUs
- **Add 25% headroom**: Prevent thermal throttling, extend MTBF
- **80+ Gold minimum**: Platinum/Titanium for always-on systems
- **Fully modular**: Essential for clean cable management

### **Example PSUs**
| PSU | Watts | Efficiency | Price | Use Case |
|-----|-------|------------|-------|----------|
| COUGAR GR 1000W | 1000W | 80+ Gold | $190 | Budget 6-GPU |
| EVGA SuperNOVA 1000 P2 | 1000W | 80+ Gold | $210 | Mid-tier |
| EVGA SuperNOVA 1600 P2 | 1600W | 80+ Platinum | $280 | High-end |
| Seasonic PRIME TX-1600 | 1600W | 80+ Titanium | $654 | Enterprise |

## Power Consumption Estimates

When the server will run continuously, convert wattage into approximate monthly electricity cost for the stated deployment location. Show the math explicitly:

```text
monthly_kWh ≈ (average_watts ÷ 1000) × 24 × 30
monthly_power_cost ≈ monthly_kWh × local_$per_kWh
```

For location-specific hosting questions (for example Marion or Cedar Rapids, Iowa), state the utility rate assumption you are using and compare options on both:
- **Capex**: acquisition cost of GPUs + PSUs still needed
- **Opex**: expected monthly power cost at realistic utilization, not only nameplate TDP
- **Longevity**: thermals, PSU loading, warranty/return path, and likely resale value

| Configuration | GPU Load | Total Load | PSU Requirement |
|---------------|----------|------------|-----------------|
| 6× RTX 4060 Ti 16GB | 280W × 6 = 1,680W | ~1,830W | 2× 1000W Gold |
| 6× RTX 4070 Ti 12GB | 285W × 6 = 1,710W | ~1,860W | 2× 1000W Gold |
| 6× RTX 4090 24GB | 450W × 6 = 2,700W | ~2,850W | 3× 1000W or 2× 1600W |
| 6× RTX 3090 24GB | 350W × 6 = 2,100W | ~2,250W | 3× 1000W |
| 6× AMD R9700 32GB | 270W × 6 = 1,620W | ~1,770W | 2× 1000W Gold |

## Thermal Guidelines

### **Mining Rig Considerations**
- **AAAwave Sluice V2**: Supports 12 GPUs, excellent airflow
- **GPU spacing**: Minimum 2 slots between GPUs for heat dissipation
- **Ambient temp**: <30°C optimal for component lifespan
- **Fan curves**: 70-80% speed at 70°C GPU temp
- **Dust filters**: Clean monthly to prevent thermal degradation

### **Thermal Paste Application**
- **Quality paste**: Arctic MX-6 ($15), Noctua NT-H2 ($18)
- **Application**: Thin, even layer, no air bubbles
- **Replacement**: Every 2-3 years or if temps increase >10°C

## Pitfalls

- **Do not optimize blindly for sticker performance**: tie the recommendation to the host's actual workload, concurrency target, and duty cycle first.
- **Do not price the whole machine when the user asked for the remaining BOM**: separate owned parts from required purchases.
- **Do not return Amazon-only recommendations for value builds**: include used-market options such as eBay when the user cares about budget efficiency.
- **Do not ignore operating cost**: a cheaper GPU stack can be worse over time if power draw is much higher for a 24/7 host.
- **Do not recommend reusing an old mismatched GPU without checking fleet impact**: legacy cards can complicate drivers, thermal layout, and scheduling, and may drag down a mixed setup.
- **Don't underestimate power**: 6× high-TDP GPUs need 3+ PSUs, not 1-2
- **Don't ignore thermal**: Open-frame mining rigs need clean airflow paths
- **Don't buy cheap risers**: $20 PCIe risers cause instability under load
- **Don't exceed 75% PSU load**: Reduces efficiency, increases heat, lowers MTBF
- **Don't assume used GPU warranty**: Mining cards may have 50% duty cycle history
- **Don't forget auxiliary costs**: Thermal paste ($15), risers ($40×6), cable management
- **Don't mix GPU generations**: Different TDPs and VRAM create bottlenecks
- **Don't overlook PCIe lane limits**: Threadripper Pro 3945WX has 128 lanes (plenty)
- **Don't forget 12VHPWR cables**: RTX 40-series needs native 12VHPWR or adapters
- **Don't deploy on public Vercel**: If storing private training data or API keys

## Verification Checklist

Before purchasing:

```
□ Total budget within range (including shipping)
□ Total VRAM meets workload requirements
□ PSU capacity with 25% headroom
□ GPU dimensions fit chassis spacing
□ PCIe risers compatible with motherboard
□ 12VHPWR cables included or purchased
□ Thermal paste and anti-static wrist strap
□ Return policy for defective units
□ Warranty coverage (new vs. used)
□ Power outlet capacity (220V vs. 110V)
□ Cooling/ventilation in deployment location
```

## References

- `references/used-gpu-bom-and-hosting-cost-checklist.md` — remaining-BOM framing, used-market sourcing checklist, mixed-GPU warnings, and monthly power-cost comparison method for always-on hosts.
- `references/gpu-pricing-database.md` — Current pricing for RTX 30/40/50-series, AMD AI PRO, and used market
- `references/psu-sizing-calculator.md` — PSU capacity formulas and recommendations by GPU count
- `references/thermal-management-checklist.md` — Thermal best practices for multi-GPU systems
- `references/budget-optimization-framework.md` — Decision framework for new vs. used, current vs. next-gen
- `references/gpu-comparison-matrix.md` — Side-by-side GPU specs, TDP, price, VRAM efficiency

## Example BOM Template

```markdown
# GPU Server Build BOM

## Configuration
- GPUs: {model} × 6
- PSUs: {model} × {count}
- PCIe Risers: 8-lane × 6
- Thermal Paste: {model} × 1

## Pricing
| Component | Qty | Price Each | Subtotal | Link |
|-----------|-----|------------|----------|------|
| GPU | 6 | $XXX | $XXXX | [Amazon](url) |
| PSU | 2 | $XXX | $XXX | [Amazon](url) |
| Risers | 6 | $XX | $XX | [Amazon](url) |
| **TOTAL** | | | **$XXXX** | |

## Specifications
- **Total VRAM**: {VRAM per GPU} × 6 = {total} GB
- **Peak Power**: {GPU_TDP} × 6 + 150W = {total} W
- **PSU Capacity**: {PSU_count} × {PSU_watts} = {total} W
- **Load Percentage**: {peak_power} / {psu_capacity} = {percent}%

## Best For
{Specific use cases: LLM fine-tuning, inference, diffusion, etc.}
```

## Next Steps

1. Add all items to shopping cart
2. Check for bundle/subscribe & save discounts
3. Verify PSU cables (12VHPWR for RTX 40-series)
4. Purchase thermal paste and anti-static wrist strap
5. Verify return policy and warranty coverage
6. Check power outlet capacity in deployment location
7. Plan for dust filtration and cooling