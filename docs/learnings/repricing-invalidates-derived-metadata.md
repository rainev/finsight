---
name: repricing-invalidates-derived-metadata
description: Recompute reliability, ROE bridges, and period-specific claims whenever a scenario range is repriced.
metadata: { type: gotcha }
---
Changing a claim, equity anchor, share denominator, or scenario value invalidates every downstream
derived field. Recompute reliability movement, beginning/current common equity, reported ROE,
modeled ROE caps, traces, and baseline metadata from the repaired inputs.

**Why:** Batch 34 repaired BRO, NTRS, and STT values while retaining stale reliability ratios; it
also applied current preferred claims to earlier balance-sheet periods. The displayed arithmetic
replayed, but public reliability fell back to `RELIABILITY_PAYLOAD_INVALID` and historical ROE was
misstated.

**How to detect / apply:** After repricing, recalculate every derived field and assert it against the
final range. Store beginning and ending claim ranges separately and source each period independently.
