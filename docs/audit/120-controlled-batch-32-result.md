# Controlled Universe Reset Batch 32 Initial Result

Date: 2026-09-03
Status: **user-confirmed on 2026-09-03**

## Outcome

- Pass: **1/10** — GDDY
- Conditional: **9/10** — DDOG, KEYS, LITE, HPE, VRT, AVGO, MRVL, SNDK, Q
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| DDOG | Conditional | $46.19 | $71.67 | $106.56 | Low | SBC/net dilution, convertible settlement, capped calls, multi-class shares, and growth fade |
| KEYS | Conditional | $66.01 | $122.80 | $182.13 | Low | Acquisitions/divestiture, integration, commitments, deferred compensation, and acquired cash conversion |
| GDDY | Pass | $93.80 | $166.32 | $255.58 | Low | Five-year cash history and current cash/net-debt/share bridge reconcile; the new revolver is undrawn |
| LITE | Conditional | $11.87 | $26.70 | $77.08 | Low | The latest release fixes stale bridge inputs but lacks a full cash-flow statement, so cycle margins remain governed |
| HPE | Conditional | $4.33 | $12.39 | $37.83 | Low | Juniper/Financial Services, preferred conversion/dividends, inventory conversion, and commitments |
| VRT | Conditional | $22.53 | $89.35 | $167.22 | Low | Acquisitions, contingent consideration, order conversion, working capital, and high growth fade |
| AVGO | Conditional | $73.34 | $149.78 | $259.60 | Low | VMware, commitments/RPO, SBC, leverage, Apple/AI arrangements, and a $29B maximum backstop |
| MRVL | Conditional | $14.49 | $30.35 | $53.69 | Low | Celestial/XConn, contingent consideration, preferred conversion, acquisition shares, and capacity commitments |
| SNDK | Conditional | $46.26 | $168.21 | $429.94 | Low | The latest full year is a storage-cycle outlier; limited standalone history and commitments remain material |
| Q | Conditional | $0.36 | $26.02 | $71.42 | Low | Carve-out history, new debt/interest, parent transfers, NCI, environmental claims, and limited standalone history |

These are baseline decision ranges, not predictions or recommendations. All ten ranges are finite,
ordered, and base-positive. No unavailable input was replaced with zero.

## Controlling sources

| Ticker | Accession | Filed | Report period | Cutoff-safe event evidence |
| --- | --- | --- | --- | --- |
| DDOG | 0001628280-26-054458 | 2026-08-06 | 2026-06-30 | — |
| KEYS | 0001601046-26-000024 | 2026-06-04 | 2026-04-30 | — |
| GDDY | 0001609711-26-000088 | 2026-07-31 | 2026-06-30 | 8-K 0001609711-26-000092 |
| LITE | 0001628280-26-030777 | 2026-05-06 | 2026-03-28 | 8-K 0001628280-26-055726 full-year release |
| HPE | 0001645590-26-000055 | 2026-06-02 | 2026-04-30 | 2025 10-K conversion terms; 8-K 0001645590-26-000074 dividend |
| VRT | 0001628280-26-050609 | 2026-07-29 | 2026-06-30 | — |
| AVGO | 0001730168-26-000054 | 2026-06-09 | 2026-05-03 | 8-Ks 0001193125-26-275077 and 0001193125-26-295589 |
| MRVL | 0001835632-26-000019 | 2026-05-28 | 2026-05-02 | — |
| SNDK | 0001628280-26-029401 | 2026-05-01 | 2026-04-03 | 8-K 0001628280-26-053346 full-year release/buyback authorization |
| Q | 0002058873-26-000030 | 2026-08-04 | 2026-06-30 | — |

All ten packets and structural filings parsed. HPE, VRT, AVGO, and MRVL reused validated
difficult-106 evidence; the other six were captured. Wrapper-level parser periods are diagnostic
only; source-receipt dates and exact fact periods control.

## Load-bearing treatments

- LITE uses the August release's `$3.014B` revenue, `$2.7384B` cash/investments, `$1.6374B` debt,
  and at least `91.5M` common-equivalent shares. Its history profile keeps a coherent 2026-03-28
  revenue/cash pair because the release supplied no full cash-flow statement.
- SNDK uses the August release's `$20.248B` revenue, `$11.671B` OCF, `$177M` capex, `$4.762B`
  cash, `$1.777B` marketable securities, zero debt, and `155M` diluted shares. A governed
  `1% / 8% / 16%` cash-margin range prevents the current storage boom from becoming the forecast.
- HPE adds `$1.357B` May H3C proceeds and subtracts the `$750M` May term-loan repayment from cash
  and debt. Every scenario includes the `76.056M–93.168M` conversion range and five preferred
  dividends. Its financing-cost input is explicitly a mixed-finance proxy.
- MRVL deducts the full `$647.6M` contingent-consideration liability once. It does not also add the
  `22.4M` shares represented inside that liability; NVIDIA's `21.8M` conversion remains.
- GDDY uses `$1.1555B` cash and `$3.7744B` net debt; `$3.8169B` gross principal is diagnostic. Its
  new `$1.2B` revolver replaced an undrawn `$1.0B` facility.
- AVGO's bear case deducts the full `$29B` maximum AI-rack backstop. RPO and Apple agreements
  support revenue visibility only and are not added to cash.
- KEYS deducts its `$39M` deferred-compensation liability. Operating commitments stay inside
  post-cost cash conversion and are not deducted again as debt.
- SBC stays inside reported OCF and is never subtracted again as cash; material future net dilution
  remains a Conditional dependency.

## Independent challenge

The challenge initially found one Critical and four Important issues: stale LITE/SNDK releases,
omitted HPE conversion/event state, double-counted MRVL consideration, and false GDDY cash/debt
treatment. Two further integrity issues—GDDY's contradictory public label and LITE's mixed-period
history observation—were repaired in successors.

Final G/H disposition: **0 Critical / 0 Important**. The challenger replayed all 30 DCF scenarios
exactly, verified event-document hashes and sensitivity directions, and accepted Pass 1 /
Conditional 9 / Withheld 0. Remaining Minor caveats are the disclosed HPE mixed-finance proxy,
LITE's older coherent cash-flow anchor, and GDDY's broad Low-reliability range.

## Determinism and real-consumer verification

- Source replay A/B: byte-identical tree `25383b26651f1386fb9e35ca4ffd31fac4f132eee18bb613ffc80b17408df535`
- Structural replay A/B: byte-identical tree `f5ad61771d3b0076cd8a9fa9aef78e82c5929b5c192450e7c29742130909152f`
- Event evidence tree, cache excluded: `ceef8dabdfe28ef89118d115bd6f16e4da63aabf5c07b7b18302986c3bbae4a9`
- Final G/H: 21/21 files byte-identical; report `206d47324bac2ce8d0bcb48158e06d6645534f81d934f1c667afb08390d1815f`
- Final candidate tree: `ad3172913d12eebe6394fcbb36fd6baa11619dccda177d6b47e0977d36c8fae4`
- Focused Batch 32 tests: **10 passed**
- Complete backend suite: **1,556 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated catalog: **320** — 114 available / 196 conditional / 10 unavailable; artifact tree
  `39ac7ea007ad9a01324b864c9da66c0f5280a0fb3955b0dd9cb826e0df891602`
- Real API: 320 list, 320 detail, 320 calculator/default parity; zero private leaks
- Exact detail/catalog parity: 320/320; forbidden serving imports: 0
- API receipt: `9f2797029f83ff1c743f3e19f448065931ce673338587f7d6918ac1e27615570`
- Detail receipt: `54d0c34f7afc24e6ad83ad4672bfee85218c9bdb5ff49a9eebd37709f34b99ee`
- Catalog manifest: `dce0c9052bbf64dd127fbee69341896487fa36f4918c7898e55add9f4cfb2887`
- Pre-confirmation watchlist remains **197** — 187 Conditional / 10 Withheld; SHA-256
  `44535d4d8a71ab1c183de9ba156b548df280bb25a5c23bb23e7b13dd87404759`
- Automatic-withheld history remains **20**; SHA-256
  `7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`
- Tracked serving catalogs and frontend data remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-09-03. DDOG, KEYS, LITE, HPE, VRT, AVGO, MRVL, SNDK, and Q entered
the Recovery Learning Watchlist; GDDY did not because it passed. The confirmed watchlist is now
**206 companies** — 196 Conditional / 10 Withheld, SHA-256
`942df6fa3e41b45d4e2a9bc292750b1fd7fce188c52ee1c68a62b7f36d9cd258`.

Nothing was Withheld in Batch 32, so no recovery attempt or withheld-register entry was needed.
The cumulative automatic-withheld history remains unchanged at twenty entries, SHA-256
`7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`.
Batch 33, serving promotion, merge, push, and deployment remain outside this confirmation.
