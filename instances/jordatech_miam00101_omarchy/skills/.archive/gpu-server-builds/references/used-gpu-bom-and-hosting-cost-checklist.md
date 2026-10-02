# Used GPU BOM and Hosting Cost Checklist

Use this note when the user wants a value-oriented multi-GPU server recommendation, especially for an existing host with some parts already owned.

## Frame the task correctly

Start by separating:
1. Owned parts already on hand
2. Required remaining purchases
3. Optional upgrades or future swaps

If the user gives a remaining-parts budget, do not restate full-system cost as if the owned CPU/RAM/storage/case still need to be bought.

## Recommendation shape

For each candidate BOM, include:
- 6 GPU model and quantity
- PSU model and quantity
- Direct purchase URLs for GPUs and PSUs
- Whether the listing is new, used, refurb, or open-box
- Subtotal for remaining parts only
- Total VRAM
- Estimated average power draw under the intended workload
- Approximate monthly electricity cost at the stated utility-rate assumption
- Short note: why this build is good for the user's actual host job

## Used-market sourcing

When budget matters, include eBay or other used-market listings, not just Amazon/new retail.

Minimum cautions to state:
- Mining history may be unknown
- Fan/bearing wear and hotspot temps matter more than cosmetic condition
- Favor listings with clear photos, serial labels, return windows, and seller history
- Prefer matched lots when buying 6 identical GPUs, but only if the lot premium is reasonable
- Account for shipping and tax in the BOM subtotal

## Mixed-GPU warning

If the user mentions an old card they already own, evaluate whether it should be excluded.

Common reasons to exclude a legacy GPU from a 6-GPU host:
- materially lower VRAM or compute tier than the main fleet
- older architecture with weaker driver/toolchain support
- extra heat and slot use for little practical throughput
- forces job scheduling complexity or special-case routing

A legacy card is only worth keeping if it has a distinct isolated role, such as display output, low-priority batch jobs, or compatibility testing.

## Hosting-cost method

For 24/7 hosts, compare capex and opex together.

Use explicit assumptions:
- average watts under expected utilization, not only peak TDP
- utility rate in $/kWh for the stated location
- 24 hours/day × 30 days/month unless a different duty cycle is stated

Formula:

```text
monthly_kWh ≈ (average_watts ÷ 1000) × 24 × 30
monthly_cost ≈ monthly_kWh × $/kWh
```

## Decision rule of thumb

For an always-on host, rank options by:
1. Fit to real workload
2. Remaining-parts budget fit
3. VRAM and throughput per dollar
4. Monthly power cost
5. Operational simplicity: identical GPUs, sane PSU loading, easy replacement path
6. Longevity: thermals, warranty/return path, resale value
