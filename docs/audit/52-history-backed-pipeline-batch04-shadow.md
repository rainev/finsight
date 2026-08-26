# History-backed valuation pipeline and Batch 04 shadow

**Valuation date:** 2026-08-14

**Status:** implemented and pipeline/API verified; user confirmation needed. No serving promotion,
watchlist change, Batch 05/06 replay, Batch 07 processing, merge, push, or deployment occurred.

## Outcome first

The core U.S. pipeline now builds source-linked company-history profiles before using governed
policy fallbacks. Operating FCFF, bank residual-income, utility/dividend, and REIT/FFO lanes share
the same three-to-five-year history contract. Raw observations remain private; public v1.2 output
adds only the history policy version, years used, normalization basis, and source mix.

The authorized Batch 04-only shadow produced:

- Attempted: **10/10**
- Numeric: **10/10**
- Pass / Available: **4/10** — MCD, TJX, HD, ROST
- Conditional: **6/10** — F, GPC, HAS, LOW, NKE, MGM
- Withheld: **0/10**
- Reliability: **0 High / 0 Medium / 10 Low**
- Serving artifacts changed: **no**
- Recovery Learning Watchlist changed: **no**

| Ticker | State | Prior base | History base | Change | History treatment |
| --- | --- | ---: | ---: | ---: | --- |
| F | Conditional Low | $11.59 | $8.51 | -26.6% | Five-year normalized earnings; captive-finance dependency retained |
| GPC | Conditional Low | $44.24 | $55.48 | +25.4% | Historical cash margin; acquisition/working-capital growth override retained |
| HAS | Conditional Low | $53.85 | $41.87 | -22.2% | Historical cash margin; impairment/transition growth override retained |
| LOW | Conditional Low | $130.81 | $128.56 | -1.7% | Four-year cash history; housing-cycle override retained |
| MCD | Available Low | $154.30 | $142.95 | -7.4% | Five-year company-history cash margin and growth |
| TJX | Available Low | $78.92 | $73.53 | -6.8% | Five-year current-concept cash margin and growth |
| NKE | Conditional Low | $23.35 | $32.71 | +40.1% | Historical cash margin; turnaround growth override retained |
| HD | Available Low | $186.48 | $187.11 | +0.3% | Five-year company-history cash margin and growth |
| ROST | Available Low | $137.96 | $113.85 | -17.5% | Five-year current-interest cash margin and growth |
| MGM | Conditional Low | $59.76 | $60.71 | +1.6% | Historical cash margin; casino-cycle growth override retained |

All ten remain Low because the combined scenario movements exceed the unchanged 40% Low threshold.
History did not erase material-event uncertainty or automatically improve confidence.

## Source and model controls

- Company history uses the latest five cutoff-eligible annual periods, with three required for a
  full history classification; LOW has four and the other nine have five.
- Base assumptions use the median. Four or more observations use the historical 25th/75th
  percentiles; smaller valid sets use observed minimum/maximum.
- Conditional issuers retain their dated event/specialist growth overrides. History normalizes the
  operating or earnings anchor without pretending the material dependency disappeared.
- TJX and ROST initially exposed stale alias-series traps. Their final history uses current,
  source-linked annual revenue and interest concepts aligned to OCF/capex periods.
- WACC, terminal growth, share ranges, and bridge/event overrides remain labeled FinSight policy.
- The 5% materiality rule and existing reliability thresholds are unchanged.

## Verification evidence

- Focused history/Batch 04/routing/public tests: **128 passed, 3 skipped**.
- Complete backend suite: **1,269 passed, 3 skipped, 1 existing Passlib warning**.
- Frontend production build: **passed**, 1,695 modules transformed.
- Final run-e/run-f outputs are byte-identical. Report SHA-256:
  47cc8b20102597b60cb1ee9109b375d171603bc169cdf814e1d136232d94b969.
- Real staged FastAPI list: HTTP 200, exact count 10.
- Detail and calculator GET: 10/10 HTTP 200; exact base parity; historical periods locked.
- Public history leakage scan: zero private profiles, observations, flow sources, bridge sources,
  source manifests, or input provenance.
- Protected serving hashes and watchlist hash were unchanged.

## Remaining verification limits

- Browser control was unavailable in this environment. The frontend production build passed, and
  the existing assumption grid accepts the new optional scalar metadata, but the visual browser
  flow is not firsthand verified in this run.
- Three delegated independent reviewers did not return findings and were closed. Sol performed the
  final source, arithmetic, model-override, public-safety, deterministic, and real-API checks, but
  this does not substitute for the planned independent challenge.

## Gate

The history layer is active in the core pipeline and the Batch 04 shadow is staged only. Treat this
phase as **verified with stated review limitations — user confirmation needed**. Batches 05 and 06
remain untouched and require separate manual retry instructions.

**Subsequent status:** the user confirmed and promoted this exact candidate in
[Audit 53](53-batch04-history-promotion.md).
