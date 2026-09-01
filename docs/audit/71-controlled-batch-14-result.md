# Controlled Universe Reset Batch 14 Initial Result

Status: **user confirmed on 2026-08-29**. Exactly the ten frozen Batch 14
Health Care issuers were processed at the 2026-08-14 valuation date. No recovery, Recovery
Learning Watchlist or cumulative-withheld-register mutation, tracked serving promotion, Batch 15,
merge, push, or deployment was performed.

## Result

- Pass: **1/10** — IDXX
- Conditional: **9/10** — TECH, HCA, REGN, BIIB, VRTX, INCY, GILD, BSX, MCK
- Withheld: **0/10**
- Numeric: **10/10**, all Low reliability
- Cumulative after 140 processed issuers: **48 Pass / 86 Conditional / 6 Withheld**
- Cumulative numeric coverage: **134/140**
- Recovery Learning Watchlist: **83** at the initial-result stop; **92 after confirmation**

| Ticker | Outcome | Low | Base | High | Reliability | Controlling filing / period |
| --- | --- | ---: | ---: | ---: | --- | --- |
| TECH | Conditional | $8.18 | $18.82 | $33.87 | Low | `0001104659-26-056302` / 2026-03-31 |
| HCA | Conditional | $113.68 | $341.89 | $666.52 | Low | `0001193125-26-321077` / 2026-06-30 |
| REGN | Conditional | $520.07 | $775.66 | $1,201.75 | Low | `0000872589-26-000025` / 2026-06-30 |
| IDXX | Pass | $137.32 | $218.88 | $338.39 | Low | `0000874716-26-000123` / 2026-06-30 |
| BIIB | Conditional | $30.82 | $122.45 | $272.12 | Low | `0000875045-26-000075` / 2026-06-30 |
| VRTX | Conditional | $208.95 | $309.79 | $456.69 | Low | `0000875320-26-000259` / 2026-06-30 |
| INCY | Conditional | $39.54 | $76.78 | $142.64 | Low | `0000879169-26-000056` / 2026-06-30 |
| GILD | Conditional | $47.81 | $84.83 | $142.24 | Low | `0000882095-26-000031` / 2026-06-30 |
| BSX | Conditional | $12.07 | $26.92 | $49.34 | Low | `0000885725-26-000053` / 2026-06-30 |
| MCK | Conditional | $477.99 | $849.83 | $1,262.36 | Low | `0000927653-26-000234` / 2026-06-30 |

Values are USD per-share baseline decision ranges, not predictions or recommendations. Low
reliability reflects broad scenario movement. IDXX is still a Pass because its source, bridge,
history, and ordinary operating model are complete without a named material provisional event.

## Frozen contract and source gate

The frozen order is TECH, HCA, REGN, IDXX, BIIB, VRTX, INCY, GILD, BSX, and MCK. The manifest has
eight core and two boundary issuers, with no replacement or skipped ticker. Its SHA-256 is
`7a80214e271840463f70cee1ce4ae9e81783d1ec99400943081bb7b90cfc1b73`.

- Reused complete SEC packets: IDXX, BIIB, VRTX.
- Fetched after cache preflight: TECH, HCA, REGN, INCY, GILD, BSX, MCK.
- Structural parsing: 10 attempted / 10 parsed / 0 failed.
- The initial structural run was interrupted after completing TECH and HCA evidence. The resumed
  run used a fresh immutable root, reused those complete partial results plus IDXX/BIIB/VRTX, and
  captured only REGN/INCY/GILD/BSX/MCK.
- TECH's June 30 10-K was filed after the cutoff. The correct controlling financial filing is the
  March 31 10-Q. Its cutoff-eligible August 10 preliminary merger proxy was separately captured and
  hash-bound for the pending event.
- All controlling financial filings were filed by 2026-08-14.
- Source replay A/B reused all ten with zero fetches and matched exactly:
  `a94575691e6cc20fb502220a3d71e2806c488dc14cc46a8a00a7df7bc8c7ac9b`.
- TECH event-source replay A/B matched exactly:
  `0cd9b6a2f49667518858edeb12a422ed098512e979cf1b3a64aa6b227340e1e5`.
- Structural replay A/B reused all ten and matched exactly:
  `193a0f4e819e8dfb7be889b78689b56a6c87b8ee31069b6c69b916ca096ba41b`.
- Protected serving roots stayed unchanged.

Every Batch 14 structural wrapper has a misleading top-level period diagnostic. Filing selection
uses the bound source receipt's filed/report dates and each fact's own period; every private result
marks the wrapper diagnostic `used_for_selection: false`.

## Outcome decisions

- **TECH Conditional:** current standalone FCFF remains usable, but the pending $73-per-share cash
  merger is kept separate from intrinsic value and the Wilson Wolf forward contract can require up
  to $1B additional investment. No merger consideration is probability-weighted into the range.
- **HCA Conditional:** debt and $3.433B NCI reconcile, while the $1.464B professional-liability
  reserve is ranged 100%/50%/0% because a complete source-linked payment roll-forward is absent.
  Operating leases remain post-rent operating items and are not deducted twice.
- **REGN Conditional:** complete cash/securities, debt/finance lease, dual-class shares, and $67.2M
  accrued contingent consideration reconcile. Collaboration revenue and $228.9M acquired IPR&D
  remain material to recurring cash conversion.
- **IDXX Pass:** five comparable annual periods, current cash, debt, shares, and the supplier-finance
  treatment reconcile. A $2.3M prior acquisition claim is conservatively retained; it is immaterial
  to the ordinary diagnostics/consumables baseline.
- **BIIB Conditional:** Apellis closed May 14 for $5.410B with new financing. The partial-period TTM
  cash margin is excluded; annual history supplies the range, with contingent consideration and the
  appealed Genentech amount explicitly reserved.
- **VRTX Conditional:** this is a pre-Crinetics standalone intrinsic range. The pending approximately
  $10B transaction and $4.5B term-loan commitment remain separate event evidence; no post-close
  object or deal probability is invented.
- **INCY Conditional:** current TTM cash is excluded from normalization because of the one-time
  $246M CMS/OPZELURA resolution. Reported revenue is not incorrectly reduced. July Vega cash and
  contingent consideration are incorporated once through a bounded post-event bridge.
- **GILD Conditional:** current TTM cash is excluded because $12.15B acquired-IPR&D addbacks and
  $11.318B acquisition cash make it non-comparable. The range uses annual history, current
  post-event cash/debt, and explicit Arcellx/Tubulis/Ouro contingent states. Negative NCI is not
  credited as a common-equity asset.
- **BSX Conditional:** Penumbra/other acquisitions, $257M contingent consideration, $242M NCI,
  $282M litigation reserve, and July restructuring cash are included once. Combined cash history
  remains integration-dependent.
- **MCK Conditional:** the bridge includes opioid liabilities plus redeemable/nonredeemable NCI.
  The $496M July payment reduces June cash and the booked reserve equally; the separate $7.9B
  settlement amount is retained as evidence and not added again.

## Independent challenge and repairs

The Luna xhigh challenge reproduced the FCFF arithmetic and initially identified three Critical
and four Important findings. Repairs were:

- remove INCY's incorrect $246M revenue haircut while retaining a cash-history exclusion;
- move HCA and REGN from Pass to Conditional and bind their material dependencies;
- exclude BIIB's partial post-Apellis TTM cash margin;
- add BSX's omitted $282M litigation reserve;
- add NCI/preferred/temporary-equity absence evidence and explain GILD's negative NCI;
- retain MCK's $7.9B settlement fact without double counting it.

The exact final candidate recheck found no remaining Critical or Important issue. Final
classification is Pass 1 / Conditional 9 / Withheld 0.

## Determinism, tests, build, and real API

- Final candidate A/B full-tree SHA-256:
  `fca8936b4756492d60b0f38601e5867e9970e2243ad41461d166d0a71887dcf0`
- Generated-private tree SHA-256:
  `6a088363861878a3f8cca08cb2e52443debc15dca839eb5b0a1ebc1e6d174e6e`
- Staged-public tree SHA-256:
  `f6d4d0be513c80fee97854f7cc18684538a97ecff1507acead46e323de6a2df6`
- Focused Batch 14 tests: `4 passed`
- Full backend suite: `1,506 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- Isolated cumulative catalog: `140` artifacts, Batches 01–14
- Catalog availability: `48 available / 86 conditional / 6 unavailable`
- Catalog publication: `134 review-required / 6 withheld`
- Catalog artifact-tree SHA-256:
  `5a888569384dffcd36f74f82930116d67fac1f3093b7f0cd73570c2d1028a275`
- Real localhost FastAPI list: HTTP 200, exact count 140
- Detail/catalog parity: 140/140; exact Batch 14 staged parity: 10/10
- Calculator GET parity: 140/140; all ten Batch 14 calculators route to the operating family
- Calculator default POST parity: 134/134 numeric HTTP 200; six prior Withheld return HTTP 400
- Private leaks: 0
- API receipt SHA-256:
  `ad84e327dbed016a172d77f99a7d10cd9d1956236875130b99b9deade7b491dd`

The API used an isolated untracked catalog and local auth harness with `save=false`. It verifies
real list/detail/calculator HTTP behavior, not production authentication, database/object-storage
persistence, or serving promotion.

## Confirmation and bookkeeping

The user confirmed the Batch 14 result on 2026-08-29. The nine Conditional companies were added
to the Recovery Learning Watchlist with `recovery_outcome: not_applicable`; IDXX was not added
because it passed. None consumed a withheld-company recovery attempt.

The watchlist now contains 92 entries: 86 Conditional and six still-Withheld. Its SHA-256 is
`389e2a9de5ff22d35b86f2026bd285617fc990877f4be59e010d9dca00922479`.

The cumulative withheld register remains byte-identical at ten entries and SHA-256
`0205878089044e64002b8e181821939c266681e5258b882d2749ef3d068ae109`. Focused Batch 14,
watchlist, and withheld-register verification passed: `10 passed`.

Do not start Batch 15, promote or activate a tracked serving catalog, merge, push, or deploy
without a separate explicit signal.
