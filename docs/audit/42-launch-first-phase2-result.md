# Launch-first Phase 2 result

## Exact Batch 03 result

- Attempted: **10/10**.
- Numeric: **8/10**: 3 retained source-bounded values and 5 Conditional Low baselines.
- Not available: **2/10**: ECHO and PSKY.
- Legacy withheld count: **0**; `not_available` is the retail state.
- Serving artifacts changed: **no**.
- Recovery Learning Watchlist changed: **no**.

| Ticker | Availability | Low | Base | High | Method / hard failure |
| --- | --- | ---: | ---: | ---: | --- |
| LYV | Conditional Low | $0.00 | $41.59 | $105.47 | event-normalized cash FCFF; bear equity floor |
| ECHO | Not available | — | — | — | deconsolidation/spectrum/debt/share object remains unbounded |
| NWSA | Available Low | $4.77 | $23.88 | $35.11 | retained source-bounded cash FCFF |
| GOOGL | Conditional Low | $51.10 | $134.10 | $251.97 | AI-commitment-adjusted cash FCFF |
| TTD | Available Low | $19.69 | $36.10 | $54.41 | retained source-bounded cash FCFF |
| DIS | Available Low | $29.75 | $64.75 | $127.90 | retained source-bounded cash FCFF |
| APP | Conditional Low | $30.70 | $246.41 | $425.89 | normalized cash FCFF with historical capex and claims reserve |
| FOXA | Conditional Low | $1.97 | $29.60 | $118.95 | rights-adjusted broadcast cash FCFF |
| TKO | Conditional Low | $0.00 | $32.94 | $76.92 | sports-rights normalized cash FCFF; reconciled Class B/NCI shares |
| PSKY | Not available | — | — | — | rejected successor-only replay has negative base despite positive high |

## Corrections made under challenge

- Cash margins are derived from TTM/annual evidence rather than decorative reported anchors.
- GOOGL's $707bn commitment changes bear reinvestment; FOXA's reserve includes the separate $801m
  program-rights obligation.
- APP uses 5%/2.5%/0% asset-based unresolved-claims reserves instead of absent-as-zero; the reserve
  is a public assumption.
- FOXA ranges restricted-cash availability at 0%/50%/100%.
- TKO reconciles H1 basic shares + Class B conversion units + incremental dilution exactly to H1
  diluted shares; nonredeemable NCI is not double-counted.
- Negative residuals retain their raw private values; a disclosed zero floor is bear-only.
- Primary rejection attempts carry the actual initial Batch 03 blockers.
- Policy version was bumped to `BATCH-03-LAUNCH-FIRST-1.1`.

## Verification evidence

- Final independent valuation verdict: **PASS**, no Critical/Important open.
- Focused LF2/replay tests: **14 passed**; expanded launch-first/routing/artifact suite:
  **228 passed, 3 skipped, 1 warning** before the final four corrections, followed by the final
  focused pass.
- Final Batch 03 run-g/run-h byte-identical tree SHA-256:
  `563e97c45be47e94e36c58ef44c84f4eac5c28df49c73da5c98c1c7ddebfef7d`.
- Batches 01–03 replay-e/replay-f byte-identical tree SHA-256:
  `b874c5780350493e2ccc14e0c5f325ce43317d1c6192e394ca937ec3814d00b4`.
- Combined staged replay: **30 unique issuers, 27 numeric, 11 conditional, 3 not available**
  (NEE, ECHO, PSKY), 0 relative baselines, 0 automatic market comparisons, no serving writes.

## Gate

LF2 is **firsthand verified**. The result still needs the later real calculator/browser/API gate and
user confirmation. Batch 04, serving promotion, merge, push, and deployment remain blocked.
