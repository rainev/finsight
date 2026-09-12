# Controlled Universe Reset Batch 33 Initial Result

Date: 2026-09-03
Status: **user-confirmed on 2026-09-03**

## Outcome

- Pass: **1/10** — MRSH
- Conditional: **9/10** — AXP, AFL, AIG, WRB, CINF, FITB, MTB, BEN, HBAN
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| AXP | Conditional | $45.79 | $75.72 | $105.90 | Low | Card credit/funding, regulatory capital, and the Series D/E preferred transition |
| AFL | Conditional | $47.02 | $75.29 | $110.35 | Low | Insurance claims/reserves, Japan/US mix, FX, reinsurance, and capital |
| AIG | Conditional | $36.99 | $63.88 | $103.29 | Low | Volatile earnings, reserve development, runoff, reinsurance, catastrophes, and capital |
| WRB | Conditional | $20.71 | $31.40 | $44.79 | Low | Underwriting/catastrophe cycles, reserve development, reinsurance, and investment income |
| CINF | Conditional | $78.25 | $125.54 | $180.37 | Low | Catastrophes, reserve development, investment-market earnings, and capital |
| FITB | Conditional | $21.62 | $34.83 | $47.74 | Low | Comerica integration means current equity is known but full combined annual history is not |
| MTB | Conditional | $124.44 | $186.13 | $253.63 | Low | Credit/deposit mix, securities marks, preferred financing, funding, and capital |
| BEN | Conditional | $9.47 | $14.48 | $21.49 | Low | AUM/flows, fee pressure, client-asset segregation, NCI, refinancing, and payout variability |
| HBAN | Conditional | $9.53 | $15.21 | $20.65 | Low | Veritex/Cadence integration means current equity is known but full combined history is not |
| MRSH | Pass | $76.32 | $135.25 | $208.31 | Low | Five-year cash history and the complete cash/debt/NCI/share bridge reconcile |

These are baseline decision ranges, not predictions or recommendations. All ten ranges are finite,
ordered, and base-positive. No missing value was replaced with zero.

## Controlling sources

| Ticker | Accession | Filed | Report period |
| --- | --- | --- | --- |
| AXP | 0000004962-26-000322 | 2026-07-24 | 2026-06-30 |
| AFL | 0001628280-26-054618 | 2026-08-07 | 2026-06-30 |
| AIG | 0000005272-26-000076 | 2026-08-07 | 2026-06-30 |
| WRB | 0000011544-26-000036 | 2026-07-31 | 2026-06-30 |
| CINF | 0000020286-26-000045 | 2026-07-27 | 2026-06-30 |
| FITB | 0000035527-26-000202 | 2026-08-04 | 2026-06-30 |
| MTB | 0000036270-26-000050 | 2026-08-04 | 2026-06-30 |
| BEN | 0000038777-26-000217 | 2026-07-31 | 2026-06-30 |
| HBAN | 0000049196-26-000066 | 2026-07-28 | 2026-06-30 |
| MRSH | 0000062709-26-000195 | 2026-07-21 | 2026-06-30 |

All ten source packets and controlling filings were captured and parsed. Exact accession, report
date, filed date, and fact periods control selection; noisy wrapper-level period summaries are only
diagnostic and never select a fact.

## Load-bearing treatments

- Nine financial issuers use an equity-level residual-income/normalized-common-earnings model.
  Deposits, policy reserves, reinsurance balances, and client assets remain inside the financial
  business instead of being treated as ordinary corporate debt or excess cash.
- The nine financial ranges are capped at Conditional Low because precise regulatory/insurance
  capital, reserve, credit, or integration refinements remain material even though uncertainty is
  finite.
- Every governed ROE scenario is privately bridged to reported TTM ROE, five exact annual earnings
  observations, current common equity, and reported dividends. Negative AIG and CINF history is
  preserved rather than removed.
- AXP includes the cutoff-safe `$1.6B` Series E issuance while retaining Series D through the
  valuation date. MTB includes the `$600M` Series L preferred issuance. FITB's `$1.272791B` note
  exchange is correctly treated as equal-principal registration, not new debt.
- FITB and HBAN use current post-combination common equity rather than mixing pre- and post-deal
  balance sheets. Their incomplete combined annual records keep them Conditional.
- BEN's `$750M` note issuance and approximately `$700M` revolver repayment are treated as a net
  refinancing change, while client assets remain excluded from issuer cash.
- MRSH uses reported operating cash flow less capex plus after-tax interest, deducts `$20.561B` of
  complete current/noncurrent debt and `$250M` NCI, adds `$1.7B` issuer cash, and excludes `$12.203B`
  restricted client cash. Five-year cash margins and the current bridge support Pass.

## Independent challenge

The first challenge identified two Important issues: the governed ROE assumptions needed an
explicit bridge to reported history, and FITB/HBAN needed current post-combination equity rather
than a misleading average. Both were repaired and replayed. The final source and model challenges
found **0 Critical / 0 Important** findings. All 30 scenarios replayed exactly, source/event hashes
matched, public artifacts contained no private evidence, and calculator defaults reproduced every
baseline. Two Minor labels were corrected in the final I/J successor.

## Determinism and real-consumer verification

- Source replay A/B: byte-identical tree `bb64d3d2bcaeeae9b2ac1eac1581762888f5e2d8fb24355f88ceff5088539fec`
- Structural replay A/B: byte-identical tree `d64b6bcc38bd51e8982d85465b75bc72df2e6edd758d3e7e86554e2079d9a858`
- Event evidence tree: `e4cf7ee94baaf1a0f2cfddc75366bf53b190e964ff1089e2fdc415d542e70dd6`
- Final I/J: 21/21 files byte-identical; report `0d0bb375a2327de15019f230d71a7720469f2753e0757b2098632bca3007326e`
- Final candidate tree: `7b5aab914583a0f38e0db863fbf11222116da8a5a315becfc2e1f624dff40526`
- Focused Batch 33 tests: **13 passed**
- Complete backend suite: **1,569 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated catalog: **330** — 115 available / 205 conditional / 10 unavailable; artifact tree
  `cdb2c58055b52185c7ea7903959deaa402189f30b5ac8bbac552f83db53f191a`
- Real API: 330 list, 330 detail, 330 calculator/default parity; zero private leaks
- Exact detail/catalog parity: 330/330; forbidden serving imports: 0
- API receipt: `bcba9450ec5936ff39ff393ce1e30cc720dad2ec2e5f64e795888d4b122c8a5a`
- Detail receipt: `5c868318f961fd0cb3bdb734ae8940508e333ae205e876348b449976f99b5571`
- Catalog manifest: `324e9b64e9c163191831dda9820801067d5ec68eb9d4ea7e528be0ab2ef21ff7`
- Pre-confirmation watchlist was **206** — 196 Conditional / 10 Withheld; SHA-256
  `942df6fa3e41b45d4e2a9bc292750b1fd7fce188c52ee1c68a62b7f36d9cd258`
- Confirmed Recovery Learning Watchlist is now **215** — 205 Conditional / 10 Withheld; SHA-256
  `7f85e1c3de77ed2fad131f8d8f97d4bc1109057dae4bc9ad8d517aa6c1402907`
- Automatic-withheld history remains **20**; SHA-256
  `7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`
- Tracked serving catalogs and frontend data remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-09-03. AXP, AFL, AIG, WRB, CINF, FITB, MTB, BEN, and HBAN entered
the Recovery Learning Watchlist; MRSH did not because it passed. Nothing was Withheld, so no
recovery attempt or withheld-register entry was needed.

Recovery, Batch 34, tracked serving promotion, merge, push, and deployment remain outside this gate.
