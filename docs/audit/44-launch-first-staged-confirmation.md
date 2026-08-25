# Launch-first staged confirmation gate

## Before / after

| Surface | Before | Launch-first stage |
| --- | ---: | ---: |
| Batch 03 numeric | 3 / 10 | 8 / 10 |
| Batch 03 unavailable | 7 / 10 | 2 / 10 (ECHO, PSKY) |
| Batches 01–03 numeric | 16 / 30 source-bounded/practical before conditional recovery | 27 / 30 |
| Batches 01–03 conditional | separate batch-specific surfaces | 11 / 30 under one v1.2 contract |
| Batches 01–03 not available | multiple technical withheld states | 3 / 30 (NEE, ECHO, PSKY) |
| Calculator default agreement | absent | 30 / 30 views |
| Public schema | legacy v1.0/v1.1 | v1.2 projection with v1.1 compatibility |

## Evidence ledger

- Batch 03 final run-g/run-h tree: byte-identical,
  `563e97c45be47e94e36c58ef44c84f4eac5c28df49c73da5c98c1c7ddebfef7d`.
- Batches 01–03 replay-g/replay-h tree: byte-identical,
  `702f5b7ba7a97d57d3364b2c2694c463732c95aaa00fc3e593caa69d4505dec0`.
- Final independent valuation challenge: PASS, no Critical/Important open.
- Complete backend: 1,232 passed, 3 skipped.
- Frontend production build: passed.
- Real API 30/30 detail/calculator parity, 0 private leaks.
- Real browser operating/conditional/hard-failure/bank/REIT flows: passed; console clean.
- Protected serving roots: unchanged.
- Batch 04: not started.
- Merge/push/deploy: not performed.

## Verified / partial / blocked / deferred

- **Verified:** shared fallback/baseline contract; Batch 03 recovery; v1.2 sanitizer; 30-company
  replay; confidence/availability labels; calculator logic/endpoints; manual comparison; private EOD
  boundary; retail UI; deterministic generation; real staged API/browser behavior.
- **Implemented but production-unverified:** real Postgres migration and saved-row persistence.
- **Blocked on external data:** automatic production EOD comparisons and peer-relative baselines.
- **Deferred by the approved stop gate:** Batch 04, serving promotion, merge, push, and deployment.

## User decision

**Confirmed by the user on 2026-08-25.** The staged Launch-First behavior and evidence are approved.
This closes the LF1–LF4 user gate. It does not authorize Batch 04, serving promotion, merge, push,
or deployment; those actions still require separate explicit instructions.
