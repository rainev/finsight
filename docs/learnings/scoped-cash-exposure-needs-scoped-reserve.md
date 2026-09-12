---
name: scoped-cash-exposure-needs-scoped-reserve
description: Compare a program-specific maximum cash exposure only with the reserve recognized for that same program and period.
metadata: { type: gotcha }
---
A disclosed maximum cash exposure for one restructuring or exit program must be compared with the
recognized reserve for that same program. Do not reduce it by an aggregate reserve that also includes
older or unrelated programs.

**Why:** Batch 41 APD recovery initially compared the $925M FY2026 project-exit cash maximum with the
$786.7M aggregate project-exit reserve. That aggregate included $89.9M from FY2025. The correct FY2026
comparison was $925M less the $696.8M FY2026 reserve, leaving $228.2M of maximum unrecognized exposure.

**How to detect / apply:** Match the maximum, reserve member, program identifier, and period before
netting. Keep older reserve members separate in the private ledger, prove whether recognized reserves
are already inside reported equity, and sensitivity-charge only the remaining same-scope exposure.
