---
name: history-needs-current-concept-lineage
description: Historical normalization must reject stale alias series and align each metric to the same recent annual periods.
metadata: { type: gotcha }
---
Companyfacts can contain a valid but stale standard concept alongside a newer issuer concept. A
normalizer that stops at the first populated alias can therefore return five old revenue or interest
facts while operating cash flow and capex use the latest five years. The resulting history appears
complete but has no overlapping periods and cannot support normalization.

**Why:** Batch 04 history initially produced no annual cash states for TJX because its selected
revenue alias ended in 2018, and none for ROST because its selected interest alias ended in 2020.
Both companies had current source-linked alternatives in the same Companyfacts packets.

**How to detect / apply:** Require revenue, OCF, capex, interest, tax, and pretax facts to share the
same annual period end before computing historical cash FCFF. If a selected alias is stale, choose
the cutoff-eligible current concept explicitly, retain accession/form/unit/period lineage, and test
the repaired series across at least three comparable annual periods. Never fill a non-overlap with
zero or silently mix old and new periods.
