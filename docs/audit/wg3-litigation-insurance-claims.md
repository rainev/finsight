# WG3 litigation and insurance overlap result

Verified 2026-09-09; user confirmation pending. Scope is Batches 01–44 only.
Production, scheduling, merge, push and deployment were untouched.

| Company | Claim result | Full refresh | Reason |
|---|---:|---|---|
| COO | $272.3M net litigation claim + $0.2M NCI | Source-bound candidate | $324.8M current reserve less the separately recognized $52.5M same-scope receivable. |
| ABBV | $1.7B litigation reserve + $47M NCI | Source-bound candidate | $86M noncash-reserve/net-payment flow and acquisition payments remain diagnostic, not additional claims. |
| STE | $43.2M litigation reserve + $14.5M NCI | Review | $38.8M self-insurance remains separate; finance-lease, investment and preferred bridge evidence is incomplete. |
| CAH | $4.329B litigation carrying claims + $159M NCI | Review | $468M current opioid portion is inside $4.3B; historical $448M is not current; July payment needs a cash/claim rollforward. |
| FIS | No numeric current legal claim established | Review | $624M/$687M payment-settlement balances are operating; expected insurance funding has no recognized numeric receivable. |
| V | $386M litigation reserve net of escrow | Review | $877M payment-settlement net and $4.31B matched collateral are operating; preferred recovery/share overlap remains unresolved. |

Frozen group:
`output/us-refresh-group-verification/d1633e92ea6115cd5a628434cce463b6446d2aa2e23ea36d92242fb69e8998e1/report.json`
(report SHA-256 `4d4ee5bf3592cf129abfa0e0eb64c76ff3bf7b0cc57d79338f155ef296c6b6e1`,
implementation `3c0f7a979d98c1ca19245545cb1efc1a46a8f7e09bf33ebc967e5eb879a107fe`,
policy `21464ac571a982cab8f086b4b04010b5d921badf773e4050e530846ca7a381f5`).

Exact public-candidate changes:

- ABBV: `83.12948904671562 / 172.7466150580554 / 261.85421361578307`
  to `81.36419913508342 / 169.46550137795154 / 257.4236776089424`.
- COO: `6.726903765240069 / 25.386746111007653 / 45.11554360720105`
  to `6.908088294983093 / 25.434654312248423 / 44.070665632853796`.

Claim reclassification is value-neutral: each legacy preferred slot is split into
the litigation adjustment and NCI. COO's change comes from the current reported
share denominator. ABBV also refreshes normalized cash FCFF, current shares and a
small source-bounded investment range.

Real API evidence:
`output/us-refresh-operational-uat-20260909-wg3-abbv/uat-report.json` served ABBV
baseline → candidate → rollback exactly, reloaded without restart, rejected stale
compare-and-swap, preserved 440 entries/419 recipes and reports
`production_runtime_touched:false`.
