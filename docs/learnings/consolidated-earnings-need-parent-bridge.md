---
name: consolidated-earnings-need-parent-bridge
description: Align earnings attribution with the parent/common-equity anchor before residual-income valuation.
metadata: { type: gotcha }
---
When a residual-income model uses parent/common equity, a consolidated net-income line is not
automatically parent earnings. Subtract reported noncontrolling-interest earnings for the same
annual and YTD periods unless the selected fact is already explicitly attributable to the parent.

**Why:** Batch 34 initially used consolidated earnings for Loews and S&P Global while anchoring
equity to the parent. That overstated TTM earnings by reported NCI and made the ROE bridge false.

**How to detect / apply:** Select the configured earnings concept explicitly, inspect the statement
attribution, and record the consolidated line, NCI line, formula, periods, and parent result in the
private ledger. Never subtract NCI twice from a fact already labeled parent-attributable. See also
[[parent-attributable-earnings-already-exclude-nci]].
