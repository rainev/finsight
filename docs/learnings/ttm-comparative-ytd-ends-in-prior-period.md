---
name: ttm-comparative-ytd-ends-in-prior-period
description: TTM reconstruction must select the comparative YTD observation ending in the prior-year period, not reuse the current period end with a prior-year start.
metadata: { type: gotcha }
---
The first practical bank extractor correctly failed because it requested a prior-YTD common-
income fact with `start=2025-01-01` and `end=2026-06-30`. The actual comparative H1 observation
ends `2025-06-30`; using the current end date describes an impossible 18-month interval.

**Why:** TTM common income is `prior fiscal year + current YTD - prior-year comparable YTD`.
The subtraction is valid only when the current and comparative YTD durations cover equivalent
calendar/fiscal intervals.

**How to detect / apply:** Validate start, end, duration, accession, filing date, and form for
both YTD observations. Require the comparative end to be the corresponding prior-year date;
reject the model rather than selecting by end date alone.

