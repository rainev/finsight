---
name: annual-balance-is-not-ttm-flow
description: Carry annual balance-sheet snapshots forward, but never copy an annual flow as a current TTM flow.
metadata: { type: feedback }
---
FinSight uses annual reports as the normal baseline for balance-sheet stock items and quarterly/YTD filings to update current operating performance. A lagging annual revenue, profit, depreciation, capital-expenditure, tax, or working-capital flow is not itself a TTM amount. Scale a missing TTM flow from source-linked company-history ratios or use a governed fallback range; do not relabel the annual amount as current.

**Why:** Annual balance-sheet values are measurements at a point in time and can remain meaningful until a newer snapshot exists. Annual operating flows cover a different time interval, so copying them into a newer TTM period silently mixes periods and can distort valuation.

**How to detect / apply:** Check private normalized output for explicit `operating_ttm` and `balance_sheet_snapshot` roles. Any TTM source with `latest_annual_proxy_for_lagging_flow` is a regression; a company-history-scaled estimate must retain its range and source periods.
