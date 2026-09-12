# Controlled Universe Reset Batch 34 Initial Result

Date: 2026-09-03
Status: **user-confirmed on 2026-09-03**

## Outcome

- Pass: **0/10**
- Conditional: **10/10** — USB, L, SPGI, NTRS, BRO, PGR, TRV, KEY, TFC, STT
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Low | Base | High | Reliability | Simple reason |
| --- | ---: | ---: | ---: | --- | --- |
| USB | $26.88 | $41.91 | $56.67 | Low | Credit losses, funding mix, regulatory capital, and preferred equity |
| L | $61.27 | $94.25 | $124.30 | Low | Insurance subsidiaries, reserves, investment income, catastrophes, and parent liquidity |
| SPGI | $83.49 | $138.03 | $185.93 | Low | Ratings/data cycles, acquisitions, regulation, and content/software investment |
| NTRS | $49.72 | $78.44 | $106.46 | Low | Fee markets, securities marks, capital, preferred dividends, and client-asset economics |
| BRO | $27.28 | $44.51 | $61.88 | Low | Commission growth, acquisition integration, retention, and current equity |
| PGR | $43.72 | $80.70 | $121.92 | Low | Pricing, claims, catastrophes, reserve development, and investment marks |
| TRV | $115.90 | $201.10 | $291.32 | Low | Catastrophes, reserves, investment income, and underwriting pricing |
| KEY | $10.46 | $16.71 | $22.95 | Low | Credit costs, deposit pricing, securities marks, capital, and preferred claims |
| TFC | $32.22 | $49.88 | $67.05 | Low | Credit normalization, funding costs, capital, preferred claims, and execution |
| STT | $63.09 | $95.16 | $123.69 | Low | Fee markets, securities marks, capital, client assets, and new preferred issuance |

These are practical baseline decision ranges, not predictions or recommendations. All ten ranges
are finite, ordered, and positive. Missing values were never replaced with zero.

## Sources and model

All ten controlling filings are cutoff-safe 2026-06-30 10-Qs, filed between 2026-07-17 and
2026-08-06. The exact accession/report-date table is preserved in the source manifests under
`output/batch-34-sec-source-packets-20260903`; all ten packets and structural filings parsed
successfully. Five exact annual earnings periods plus a current TTM reconstruction were used.

Nine companies use equity-level residual-income models for banks, insurers, custodians, or asset
managers. BRO also uses an equity-level residual-income model, but its originally broader ROE range
was capped to observed history and it was downgraded from Pass to Conditional Low. Deposits, policy
reserves, reinsurance, and client assets were not treated as ordinary enterprise debt or surplus cash.

Important cutoff-event treatments are privately traced: STT's `$500M` Series L preferred issuance
was completed before cutoff and is included in the scenario claim range; KEY and NTRS redemptions
were announced but scheduled after cutoff and were not treated as completed; TFC and TRV note
offerings are retained as financing-event checks without double counting.

## Independent challenge and repairs

The independent challenge initially found five Important issues: configured common-earnings concepts
were not always selected; L and SPGI consolidated earnings were not bridged to parent earnings;
BRO exceeded its observed ROE range and included a small NCI amount; NTRS/STT preferred sensitivities
were midpoint-only; and STT's completed preferred issuance was captured but not consumed. All were
repaired. The final challenge found **0 Critical / 0 Important** findings. Remaining items are
governed Low-reliability sensitivities and parser wrapper-period diagnostics that are explicitly
excluded from selection.

## Determinism and real-consumer verification

- Source replay A/B: byte-identical tree `b9cf703e6520020654e5d6fcd848e116dfda12754bda5c2de28b43781b775b6b`
- Structural replay A/B: byte-identical tree `e35c18fb590f993c1ec48967e8e7c92de51cc84cfe71a593e48360ecd36b663a`
- Event evidence tree: `d0e9b8a9a3abe3efceb42f14d4666bffd67d86444d5e3693cc0f983b708d2821`
- Final I/J: 21/21 files byte-identical; report `920a679e0ce7c6f30dbb3246afff29da1ad1008507b494cb1935a7fcdf1ae995`
- Focused Batch 34 tests: **9 passed**
- Complete backend suite: **1,578 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated cumulative catalog: **340** — 115 available / 215 conditional / 10 unavailable; artifact tree
  `cb485bc3f6cefdeb65983e7219e9dfe9a6e23927437776096791a1a2d02fccc7`
- Real API: 340 list, 340 detail, 340 calculator/default parity; zero private leaks
- Exact detail/catalog parity: 340/340; forbidden serving imports: 0
- API receipt: `0403e7826aacbf5f70755524d19cab0a62eb8cb101402ebc1184b18a4adfe12a`
- Detail receipt: `6d7480fa6c4e633f7e0048e881279275da621cb31c24f1613370c54c54bbf75c`
- Catalog manifest: `5df805bf2b98cb0cc5a8de1f7776bee9b851277c000b118654461019b6e8bc61`
- Pre-confirmation Recovery Learning Watchlist was **215** — 205 Conditional / 10 Withheld;
  SHA-256 `7f85e1c3de77ed2fad131f8d8f97d4bc1109057dae4bc9ad8d517aa6c1402907`
- Confirmed Recovery Learning Watchlist is now **225** — 215 Conditional / 10 Withheld;
  SHA-256 `e80e4e627c054fbb4b1748e8e05a2b391e4401849dfede21f1aebab2c7763771`
- Automatic-withheld history remains **20**; SHA-256
  `7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`
- Existing tracked serving catalogs and frontend data remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-09-03. USB, L, SPGI, NTRS, BRO, PGR, TRV, KEY, TFC, and STT entered
the Recovery Learning Watchlist. Nothing was Withheld, so no recovery attempt or withheld-register
entry was needed. Batch 35, serving promotion, merge, push, and deployment remain outside this gate.
