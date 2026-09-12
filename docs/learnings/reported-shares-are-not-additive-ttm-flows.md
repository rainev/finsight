---
name: reported-shares-are-not-additive-ttm-flows
description: Select reported share denominators directly; do not apply cash-flow TTM arithmetic or assume a fixed DEI QName prefix.
metadata: { type: gotcha }
---

MRNA's refresh draft used `ttm_flow` for diluted weighted-average shares and
missed the later cover-page count because its DEI QName had a generated prefix.
The resulting apparent valuation change was a selection bug, not stale baseline
data. The reported H1 denominator is 396M; the July 24 cover count is 399,235,889.
Their approved midpoint is 397,617,944.5, which reproduces the frozen base value.

Select an actual current YTD/FY weighted-average fact. Select cover shares by
the exact DEI namespace URI and local name, not by assuming the prefix is `dei`.
Retain both dates and source contexts. Reconstructing money flows as FY + current
YTD - prior YTD does not make that operation appropriate for share averages.
