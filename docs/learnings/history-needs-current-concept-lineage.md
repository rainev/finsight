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

Batch 20 showed a narrower variant: Pentair's current TTM interest was source-linked, but the
selected standard annual interest alias ended in 2019 while revenue, OCF, capex, tax, and pretax
history continued through 2025. The pending-deal Conditional model therefore estimated each annual
interest amount from the current reported interest/revenue ratio, labeled every repaired row as
estimated, and retained the reported current amount separately.

**How to detect / apply:** If no cutoff-safe current annual concept can be selected, use a governed
nonzero sensitivity or ratio only when its valuation effect is bounded and fully traceable. Cap the
result appropriately and preserve the missing lineage as a release condition. Do not let a valid
current fact falsely make a stale annual series look complete.

Batch 23 showed the structural-filing form of the same trap. United Rentals' standardized
`PaymentsToAcquireProductiveAssets` series ended in FY2024, while FY2025 and current H1 split fleet
and other capex into issuer-extension concepts that Companyfacts did not expose. The provisional
run-rate was finite but remained Conditional. Parsing the exact FY2025 10-K found $4.149B fleet and
$379M other capex; together with $2.885B current H1 and $2.303B prior H1, exact TTM capex became
$5.110B. The higher source-backed reinvestment materially lowered value and closed the extraction
condition without a zero.

**How to detect / apply:** When a standard annual alias goes stale but current structural custom
tags prove a changed presentation, capture the matching annual filing structurally before assuming
the value is absent. Sum mutually exclusive issuer-tagged components, retain every accession,
period, unit, and component, and rerun the complete valuation because a repaired input can move the
range substantially even when the classification improves.
