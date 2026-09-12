# CAH commitment migration — source audit, 2026-09-09

Not implemented or approved. This is the next claim/timing work item, not a
current unavailable publication and not a reason to change historical results.

## Verified source

CIK 0000721371, accession 0000721371-26-000038, FY ending 2026-06-30.
Raw filing: `output/batch-13-structural-cache-20260829/filings/CAH/CIK0000721371-000072137126000038/04af6a86a030584628bbd459ddbfebbf9c394f9f6ac3a8414d8f5c1ce3bf5b68/cah-20260630.htm`.
Raw SHA-256: `9c248492d2d02d3920527701d4ad89f46ab0531327d16621e6aa72dece3e5704`.
Structural SHA-256: `ef8f6008cd228393ea11dab0939f8cc7a523c02954cabb094393d1f68fb0c675`.

## Findings and constraints

- Retained bridge combines $4.3B opioid accrual, $29M IVC accrual and $159M NCI.
  Current $468M opioid liability is included in the $4.3B, not additive.
- Primary text qualifies the reviewer concern about $213M: the $4.3B covers
  opioid matters described below; the $213M paragraph describes settlement
  agreements finalized in 2025. Do not infer an additional current liability
  from its tagged current context. Its independent current carrying amount is
  not established by that paragraph.
- FY2026/FY2025 OCF explicitly includes opioid cash payments of $417M/$798M.
  There were no material expenses recognized for those matters in those years.
  A litigation-loss QName alone therefore does not establish expense semantics.
  Historical cash normalization and future liability deductions require overlap
  reconciliation; do not deduct the same payments twice.
- Primary review also found the July2026 sixth NOSA payment of $374M. This is
  after the June balance-sheet date and must be accounted for consistently in
  both cash and the remaining claim, not added as another liability. Exact cash
  date and source-linked post-period reconciliation remain implementation work.
- Additional governmental payments are disclosed as up to $3.7B through 2038;
  the filing explicitly says future annual amounts may differ. $2.6B paid
  through July2026 is historical cumulative cash. Neither is an evidenced annual
  future payment schedule. Private plaintiffs and other claim coverage remain
  separate from the governmental aggregate.
- The historical $448M IVC settlements are not an additional current reserve.
  Recorded $29M, remaining litigation and any recovery netting need their own
  scope. Do not automatically net insurance or New York recoveries.

## Next implementation gate

Capture/hash the relevant cash-payment narratives; reconstruct comparable annual
payment coverage before altering the cash baseline. Preserve current/noncurrent
and historical/current distinctions. Require an evidenced annual payment
schedule or a defensible, explicitly reviewed PV reserve. The overlap helper's
uniform diagnostic allocation is not source evidence for payment timing.
No CAH refresh contract has been declared ready on these partial facts.
