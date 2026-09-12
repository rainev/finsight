---
name: legacy-report-date-needs-validated-envelope
description: Older parsed filings may expose a cover-share date as period_end; preserve it diagnostically and bind the verified SEC reporting period.
metadata: { type: gotcha }
---
HLT's older parsed June 2026 filing has no report_date and a top-level period_end
of July 23 from later cover shares. Its June 30 financial facts are valid.
The ingestion adapter now supplies a missing report_date only from the validated
SEC filing envelope, retaining the old top-level date as a diagnostic. Explicit
conflicting report dates still fail.

Hash the validated payload actually returned to callers. Retain the raw parsed
cache hash separately; hashing one representation and returning another creates
false tamper errors in downstream source evidence.
