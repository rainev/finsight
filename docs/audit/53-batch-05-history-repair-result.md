# Batch 05 history-backed Pass repair result

**Valuation date:** 2026-08-14

## Outcome

The revised historical-data layer is present and consumed by the core operating, bank, utility,
and REIT lanes. Batch 05 is now wired to the same source-linked history contract.

- **Pass: 4/10** — WSM, CASY, AZO, ORLY
- **Conditional: 6/10** — CCL, PHM, SBUX, DHI, RCL, NVR
- **Withheld: 0/10**

| Ticker | Prior base | History-backed base | Change | Final state | History |
| --- | ---: | ---: | ---: | --- | --- |
| WSM | $139.79 | $121.43 | -13.1% | Pass | Five annual periods; historical cash conversion and growth |
| CASY | $284.92 | $325.71 | +14.3% | Pass | Five unique annual periods; duplicate FY/TTM period removed |
| CCL | $11.68 | $11.68 | 0.0% | Conditional | Three usable cash-history periods; cruise dependency retained |
| PHM | $77.50 | $105.79 | +36.5% | Conditional | Five-year earnings history; mortgage/land dependency retained |
| SBUX | $38.04 | $38.04 | 0.0% | Conditional | Five-year cash history; store-turnaround override retained |
| AZO | $1,673.02 | $2,172.89 | +29.9% | Pass | Five annual periods; finance-lease range remains bounded at 0.22% total spread |
| DHI | $82.62 | $128.43 | +55.4% | Conditional | Five-year earnings history; mortgage/inventory dependency retained |
| RCL | $30.08 | $30.08 | 0.0% | Conditional | Three usable cash-history periods; cruise dependency retained |
| ORLY | $36.39 | $45.43 | +24.8% | Pass | Five annual periods; historical cash conversion and growth |
| NVR | $3,101.67 | $4,325.39 | +39.5% | Conditional | Five-year earnings history; lot/mortgage dependency retained |

All ten remain Low reliability because their scenario movement remains broad. History makes the
ordinary assumptions evidence-backed; it does not erase named material cruise, turnaround, or
homebuilder/mortgage dependencies.

## Controls and challenge

- Raw annual/TTM observations, formulas, and source lineage remain private.
- Public v1.2 exposes only policy version, history years, normalization basis, and source mix.
- WSM/CASY/AZO/ORLY each have five cutoff-safe source-linked annual periods.
- CASY initially counted FY and TTM twice because both ended 2026-04-30. The shared history layer
  now deduplicates a TTM observation when it is the same period as the latest annual observation.
- AZO retains a source-linked finance-lease range; bridge spread is 0.22%, below the existing 1%
  bridge limit and the 5% material-dependency threshold.
- Independent Luna-XHigh result: **PASS**, no remaining Critical or Important findings.

## Verification

- Focused history/Batch 05/artifact suite: **123 passed**.
- Complete backend suite: **1,273 passed, 3 skipped, 1 warning**.
- Frontend production build: **passed**, 1,695 modules transformed.
- Candidate-c/candidate-d byte-identical tree SHA-256:
  `93cb43db483d8ec2c1ca0801147c608606500abd15d2f39689bc7360162d913e`.
- History repair report SHA-256:
  `3fa91caecc33637b2a429dbe85237de6b46dc427cceb51e917b6af646eb779b8`.
- Real API: list/detail/calculator 10/10 HTTP 200; default parity 10/10; private leaks 0.
- API receipt SHA-256:
  `56bdfdf789c9d062b58b1bbc6bfafd6b88f8284308b7b1e3fb0313d8ad7057a8`.
- Serving artifacts changed: **no**.

## Watchlist

WSM, CASY, AZO, and ORLY were removed after verified source-bounded recovery. The Recovery
Learning Watchlist now contains 36 companies: 33 Conditional and 3 Withheld. Watchlist tests pass
3/3; SHA-256 is
`e719e29e6c60a6f6f513aa23931156927e677d8bad308b05cec9fe33be256f7c`.

Batch 06 reclassification, Batch 07, serving promotion, merge, push, and deployment were not
started.
