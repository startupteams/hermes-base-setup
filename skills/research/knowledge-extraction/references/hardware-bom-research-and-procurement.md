# Hardware BOM Research and Procurement

Use this reference when the user wants a server, workstation, or GPU-host bill of materials documented in a Git-backed knowledge repository.

## When this applies

- Re-do a server build analysis because prior recommendations were too expensive or too generic.
- Build multiple BOM options within a fixed GPU/PSU budget.
- Compare new vs used procurement sources.
- Optimize for operating cost, longevity, and local power/cooling constraints.
- The user already owns some parts and wants the BOM to cover only the missing components.

## Required framing

Anchor the document in the **actual use case** before recommending parts.

At minimum, state:
1. The intended workloads (for example: multi-model inference, Hermes workers, fine-tuning, rendering, homelab, mining-derived chassis repurpose).
2. Existing on-hand parts that should be treated as sunk cost.
3. Which budget applies only to missing parts vs whole system cost.
4. Local operating constraints: electricity cost, 120V vs 240V, heat/noise, uptime expectations, and physical chassis/rack limits.

If the prior analysis failed because it ignored one of these, call that out explicitly in the rewrite.

## BOM quality bar

For each BOM option, include:
- Exact GPU count and model.
- Exact PSU count and model.
- Estimated subtotal for the missing components.
- Estimated max draw and practical sustained draw.
- Why the option is attractive: value, VRAM, efficiency, reliability, resale, or software compatibility.
- Why the option may be risky: age, blower noise, adapter complexity, warranty, lane/slot constraints, or power spikes.
- Purchase links for the proposed parts.

When the user asks for many alternatives, keep all options in the same comparison framework so they are easy to rank.

## Source mix expectations

Do **not** rely on Amazon-only sourcing unless the user asked for that.

Prefer a source mix such as:
- eBay used listings or search URLs for value hardware.
- Newegg / manufacturer / reputable retailers for new parts.
- Direct OEM or AIB pages when they clarify specs.

If a part is likely better bought used, say so. If a part is likely better bought new because of PSU warranty or failure risk, say so.

## Budget handling

When the user gives a budget range for GPUs and PSUs, keep the BOM inside that range using the **remaining-parts** interpretation unless they explicitly say total-system budget.

If a candidate configuration is outside budget, do not force it in. Instead:
- include it in a rejected-options section, or
- mention it briefly as a benchmark and explain why it was excluded.

Examples of things worth rejecting explicitly:
- premium halo GPUs that break the budget,
- mixed-vendor pools that complicate operations,
- old cards that look cheap but have poor perf-per-watt.

## Existing-parts rule

When the user already has CPU, RAM, storage, and chassis, separate the document into:
- **Already owned / assumed present**
- **BOM for remaining purchases**

Do not pad the BOM with already-owned parts unless the user asks for a full replacement build.

## Power and hosting analysis

For Iowa/Midwest-style hosting comparisons, include simple practical analysis rather than fake precision:
- efficiency matters because 24/7 power compounds fast,
- higher-quality PSUs can improve stability and reduce stress,
- lower-power modern GPUs may win on lifetime cost even if raw throughput is lower,
- verify whether the total draw is suitable for the expected circuit.

Prefer to compare:
- acquisition cost,
- expected watts per GPU / whole rig,
- operational simplicity,
- likely MTBF / age risk,
- fit for the workload.

## Recommendation pattern

End with three clear buckets when enough evidence exists:
- **Best overall**
- **Best value / throughput per dollar**
- **Best premium / longevity**

Also add a direct note on whether odd extra GPUs already owned should stay out of the main pool. Example: keep an old Quadro out of a homogeneous 6-GPU worker if it would complicate scheduling, thermals, or throughput.

## Git + deliverable pattern

When this research is requested as a repo document:
1. Verify the correct bot branch.
2. Overwrite or create the markdown deliverable.
3. Validate that the doc explicitly ties recommendations back to the use case and budget.
4. Commit locally even if GitHub auth is broken.
5. If push fails, report the exact auth blocker and the exact `git push origin <branch>` command.
