# Controlled Universe Reset Batch 31 Initial Result

Date: 2026-09-02
Status: **user-confirmed on 2026-09-02**

## Outcome

- Pass: **2/10** — CDW, VRSK
- Conditional: **7/10** — PANW, WDAY, NOW, SMCI, NXPI, ACN, CRWD
- Withheld: **1/10** — ORCL
- Numeric: **9/10**

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| PANW | Conditional | $61.67 | $104.22 | $162.06 | Low | A major acquisition, issued equity, commitments, SBC/dilution, contingent consideration, and claims remain material |
| WDAY | Conditional | $122.22 | $204.53 | $331.01 | Low | Material SBC, rapid share-count change, repurchase funding, debt, and acquisition-intangible conversion remain load-bearing |
| ORCL | Withheld | — | — | — | — | The ordinary model cannot bound the timing and cash support for exceptionally large capex, lease, debt, preferred, and purchase commitments |
| NOW | Conditional | $53.75 | $90.98 | $145.77 | Low | The $8.776B acquisition, debt/commercial paper, SBC, timed cloud/IT obligations, and growth premium remain material |
| SMCI | Conditional | $0.00 | $9.69 | $57.41 | Low | Current cash is deeply negative while AI-server working capital, obligations, debt scope, warranty, concentration, and SBC remain cyclical |
| CDW | Pass | $35.30 | $111.36 | $191.78 | Low | Four-year-plus-current cash history and the cash/debt/share/working-capital bridge reconcile without a named material dependency |
| NXPI | Conditional | $50.76 | $90.66 | $168.11 | Low | Disposal scope, infrastructure funding, purchase obligations, restructuring, debt/NCI, SBC, and semiconductor-cycle effects remain material |
| VRSK | Pass | $56.44 | $116.47 | $195.37 | Low | Current TTM and five-year recurring analytics cash now reconcile with cash, debt/leases, zero NCI, shares, and ordinary operations |
| ACN | Conditional | $186.26 | $316.63 | $492.43 | Low | Recurring acquisitions, acquired goodwill, SBC, restructuring, utilization/FX, debt, and NCI remain material |
| CRWD | Conditional | $88.63 | $156.55 | $252.37 | Low | Acquisition/goodwill, SBC/dilution, purchase obligations, contingent consideration, claims, and high-growth fade remain load-bearing |

These are baseline decision ranges, not predictions or recommendations. All nine numeric ranges are
finite, ordered, and have positive base values. SMCI's public `$0` bear endpoint is an explicit
limited-liability floor over a privately retained `−$2.73` raw residual; it is not a substituted
missing value. ORCL has no invented value or zero.

## Controlling sources

| Ticker | Accession | Filed | Report period |
| --- | --- | --- | --- |
| PANW | 0001327567-26-000015 | 2026-06-03 | 2026-04-30 |
| WDAY | 0001327811-26-000026 | 2026-05-22 | 2026-04-30 |
| ORCL | 0001193125-26-277521 | 2026-06-22 | 2026-05-31 |
| NOW | 0001373715-26-000076 | 2026-07-23 | 2026-06-30 |
| SMCI | 0001375365-26-000014 | 2026-05-11 | 2026-03-31 |
| CDW | 0001402057-26-000065 | 2026-08-05 | 2026-06-30 |
| NXPI | 0001413447-26-000045 | 2026-07-28 | 2026-06-28 |
| VRSK | 0001437749-26-024749 | 2026-07-29 | 2026-06-30 |
| ACN | 0001467373-26-000032 | 2026-06-18 | 2026-05-31 |
| CRWD | 0001535527-26-000025 | 2026-06-04 | 2026-04-30 |

ORCL and NXPI reused validated difficult-106 packets/packages/parses. The other eight packets and
controlling packages were captured. All ten structural filings parsed successfully. Malformed
wrapper-level diagnostic dates were retained as `used_for_selection: false`; source-receipt report
dates and exact fact periods control.

## Load-bearing treatments

- VRSK was repaired after independent challenge found that automatic TTM selection stopped at
  2026-03-31. FY2025 + current H1 − prior H1 now produces 2026-06-30 revenue `$3.136B`, OCF
  `$1.5032B`, capex `$266.7M`, interest `$195.1M`, and cash-FCFF `$1.38747B`.
- CDW uses one consistent `InterestPaidNet` series for cash-FCFF: `$234.3M` FY + `$116.9M`
  current H1 − `$120.4M` prior H1 = `$230.8M` TTM. The negative mixed net-interest alias is rejected.
- PANW uses `$747M` short-term plus `$3.881B` long-term investment captions. The `$4.956B` AFS
  aggregate is diagnostic; an unexplained `$328M` residual is excluded conservatively.
- NOW counts `$4.204B` AFS securities once and excludes the overlapping `$2.073B` other-long-term
  caption. Timed cloud/IT obligations sum to `$6.302B`; supplier finance is `$28M`.
- SMCI's normalized `0.5% / 2.5% / 7%` cash margins are governed cycle assumptions because current
  TTM owner cash is `−$6.730B`. The `$4.113744B` combined debt carrying amount controls arithmetic;
  the `$4.659357B` convertible caption is retained as a scope diagnostic.
- NXPI uses structurally repaired 2026 H1 flows. The `$1.2B` aggregate infrastructure-investment
  obligation is deducted once with `$362M` NCI; `$379M/$653M` investee contexts are diagnostic.
- Operating purchase commitments remain inside post-cost cash conversion and are not deducted a
  second time as debt. Material separately identified investment obligations are reserved once.
- Reported SBC stays inside OCF; material forward net-dilution/buyback uncertainty keeps PANW,
  WDAY, NOW, SMCI, NXPI, ACN, and CRWD Conditional.
- ORCL remains withheld because a dedicated cloud/software/infrastructure schedule must reconcile
  `$55.663B` annual capex, `$39.973B` construction in progress, `$129.541B` debt, `$7.701B` finance
  leases, `$4.954B` preferred equity, `$13.309B` purchase obligations, and `$260B` uncommenced
  leases with supported incremental cash flow. A fixed-cash DCF would require invention.

## Independent challenge

Two disjoint `gpt-5.6-luna` reviewers were used under the FinSight efficiency workflow:

- High reasoning: identity, cutoff, accessions, periods, units, shares, cache reuse, bridges,
  events, commitments, investment overlap, source hashes, and public safety.
- xhigh reasoning: model suitability, acquisitions, SBC/dilution, cycles, commitments, claims,
  classification, DCF arithmetic, sensitivity directions, and calculator routing.

The source reviewer found one Critical VRSK TTM-period mismatch and one Important CDW interest-
lineage issue; both were repaired and rechecked. Final disposition: **0 Critical / 0 Important**.
The model reviewer replayed all 27 numeric scenarios exactly and passed 72 sensitivity-direction
checks. CDW/VRSK Pass, seven Conditional results, ORCL Withheld, and SMCI's bear floor were accepted.

## Determinism and real-consumer verification

- Source replay A/B: all ten reused, zero fetches, byte-identical tree SHA-256
  `b19846118324a4637cb828c7b1565fd98917059b926e5a6c2f33ae280c0b2a07`
- Structural replay A/B: all ten reused, zero reparsing, byte-identical tree SHA-256
  `ebca2ab9a9552ccbe78525019ef8568ada73adb6085da0ee02bca67a1ccb8d27`
- Final candidates E/F: 21/21 files byte-identical; report SHA-256
  `709e69c3eab54028f395dad7c60ece82c486509da9d013d5d9e9a21999ecd166`
- Final candidate tree SHA-256:
  `ba1b946819a1a3576ea842d5fab61589a5ef1146bfe89582500ebdee38f4128b`
- Focused Batch 31 tests: **11 passed**
- Complete backend suite after final code: **1,541 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated cumulative catalog: **310 issuers** — 113 available / 187 conditional / 10 unavailable;
  artifact tree `a4008c7364baefe28539e66a93ab3659fc0793e2ecd66329d177fd75a7654a91`
- Real API: 310 list, 310 detail GET, 310 calculator GET/default parity; 300 numeric POST 200,
  10 unavailable POST 400, zero private leaks
- Exact detail/catalog parity: 310/310; forbidden serving imports: 0
- Calculator/API receipt SHA-256:
  `020737c4ed8787cb0100e2328ec4a938a59c0df86dd2f4e1ec2ba23e4a147091`
- Detail/import receipt SHA-256:
  `68d1f9128663516a8b0a3c3f13e745b164a13d7960d9b59de7e7b8901574582b`
- Catalog manifest SHA-256:
  `64142a7190ab5d22e53691fe0a7e7ad3e1813e13006cba6c77e7d65ae197fbe8`
- Pre-confirmation watchlist remains **189** — 180 Conditional / 9 Withheld, SHA-256
  `00f73edfc88db2ee7374473bb4abc31e9e94c13b0e85e896bac9714375b57f16`
- Append-only automatic-withheld history remains **19**, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked serving catalogs, frontend public data, and frontend generated data remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-09-02. PANW, WDAY, NOW, SMCI, NXPI, ACN, and CRWD entered the
Recovery Learning Watchlist as direct Conditional entries; SMCI retains the explicit equity-at-risk
variant because its raw bear residual is negative. The confirmed watchlist now contains **196
companies** — 187 Conditional and 9 Withheld. CDW and VRSK were not added because they passed.

ORCL was the initial Batch 31 Withheld company. The subsequent one-attempt infrastructure recovery
in Audit 118 remained Withheld and was user-confirmed; ORCL is now recorded in both the watchlist
and cumulative withheld register. Serving promotion, Batch 32, merge, push, and deployment remain
outside scope.

Confirmed watchlist SHA-256:
`28e81df86c67da7ef79c4c4e9b1fe26f74167879bacca393dd08e1a90ff9a254`. The unchanged
withheld-register SHA-256 remains
`28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.
