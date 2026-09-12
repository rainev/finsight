# WG4 timed commitments and payment schedules

Verified 2026-09-09; user confirmation pending. Batches 01–44 only. Production,
scheduling, merge, push and deployment were untouched.

| Company | Source conclusion | Full refresh |
|---|---|---|
| MU | $6.914B current PP&E payable deducted once; $19.602B paid capex excluded | Source-bound candidate |
| KLAC | $5.970B mixed commitment; no source-backed equal-year timing | Review |
| NXPI | $1.2B total = $1.098B contributed + $102M remaining; other commitments lack timing | Review |
| AVGO | $29B is a subsequent-event maximum, not current debt | Review |
| SNDK | Mixed schedules, paid investment, guarantees and authorization cannot be stacked | Review |

Frozen group: `output/us-refresh-group-verification/38273970d9ef3a06aa98db8150df430a441aeb9a276806fad8fabdbd33343fad/report.json`.
Report SHA-256 `430c392194832c0dcf29e04844d178e36bb0b126e0e9d26aede7607976760002`;
implementation `1bbfdea76aad39382e9d11f6d5fbcc5a94233e0b7b8a1bc1593d99a15efe32aa`;
policy `1cfc5920b232d2f6ff7d4b19e0dcf3c07b33169f4c29c272526b6ec8eab4df6f`.

MU changes `29.184776884128944 / 80.97342603334381 / 153.48739296062772`
to `29.09831892444698 / 80.28792783707777 / 151.3433271564748`.
Reclassifying the same $6.914B payable from preferred equity to a dedicated
negative adjustment is value-neutral; locking the current reported diluted-share
denominator explains the value change.

Real API evidence: `output/us-refresh-operational-uat-20260909-wg4-mu/uat-report.json`
served baseline → candidate → rollback exactly, reloaded without restart, rejected
stale CAS, preserved 440 entries/419 recipes and reports production untouched.
