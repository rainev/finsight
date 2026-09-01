# Controlled Universe Reset Batch 30 Initial Result

Date: 2026-09-01  
Status: **user-confirmed on 2026-09-01**

## Outcome

- Pass: **2/10** — TDY, BR
- Conditional: **8/10** — CTSH, ON, STX, FTNT, FSLR, MPWR, PLTR, TEL
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| CTSH | Conditional | $47.55 | $78.25 | $109.16 | Low | The $1.334B acquisition, new debt/share state, restructuring, and contingent consideration remain material |
| TDY | Pass | $179.79 | $360.28 | $558.94 | Low | Five-year cash history and the cash/debt/environmental/share bridge reconcile; the current acquisition is ordinary-sized and consolidated |
| ON | Conditional | $15.09 | $23.99 | $56.03 | Low | The signed Synaptics transaction is not closed and remains separate from the current-company baseline |
| STX | Conditional | $30.89 | $84.76 | $148.47 | Low | Two typed legal-claim contexts are conservatively summed but cannot yet be proven non-overlapping |
| FTNT | Conditional | $46.01 | $74.35 | $120.65 | Low | Large inventory commitments, expansion, and review-grade investment classification remain material |
| FSLR | Conditional | $15.34 | $34.74 | $126.56 | Low | Four of five historical cash years were negative, so the finite cash-margin range is a governed FinSight assumption |
| MPWR | Conditional | $167.16 | $325.16 | $634.19 | Low | H1 stock compensation remains in operating cash flow while forward net dilution is not yet normalized |
| PLTR | Conditional | $10.05 | $22.91 | $48.38 | Low | Long-term commitments, high-growth fade, SBC/net dilution, NCI, and customer concentration remain load-bearing |
| BR | Pass | $81.22 | $162.62 | $238.65 | Low | Five-year cash history, debt, investments, contingent consideration, shares, and the exact commitment schedule reconcile |
| TEL | Conditional | $74.96 | $153.98 | $264.04 | Low | The pending Astrodyne acquisition remains separate while current acquisition/restructuring/claim effects remain material |

These are baseline decision ranges, not predictions or recommendations. All ten ranges are finite,
ordered, and have positive base values. No missing value was replaced with zero.

## Controlling sources

| Ticker | Accession | Filed | Report period |
| --- | --- | --- | --- |
| CTSH | 0001058290-26-000031 | 2026-07-29 | 2026-06-30 |
| TDY | 0001094285-26-000043 | 2026-07-24 | 2026-06-28 |
| ON | 0001097864-26-000017 | 2026-08-03 | 2026-07-03 |
| STX | 0001137789-26-000159 | 2026-08-04 | 2026-07-03 |
| FTNT | 0001262039-26-000021 | 2026-07-30 | 2026-06-30 |
| FSLR | 0001274494-26-000170 | 2026-07-30 | 2026-06-30 |
| MPWR | 0001628280-26-053275 | 2026-08-05 | 2026-06-30 |
| PLTR | 0001321655-26-000041 | 2026-08-04 | 2026-06-30 |
| BR | 0001628280-26-052243 | 2026-08-04 | 2026-06-30 |
| TEL | 0001104659-26-086509 | 2026-07-24 | 2026-06-26 |

ON, MPWR, and PLTR reused validated cutoff packets; the other seven were captured. ON and MPWR
reused current structural wrappers; the other eight were parsed from the controlling filings.
Cache-only source and structural A/B replay reused all ten with zero fetching or reparsing.
STX's wrapper-level `2028-06-30` diagnostic is explicitly rejected and never used for fact or
filing selection; the source receipt report date and exact fact periods control.

## Load-bearing treatments

- PLTR uses `$2.030047B` cash plus `$7.379052B` balance-sheet marketable securities once. Its
  `$7.591790B` AFS total is overlap proof only, not additional cash.
- FTNT uses `$1.1347B` short-term plus `$399.1M` long-term investment captions. The matching
  `$1.5338B` aggregate is diagnostic only and the review-grade classification keeps FTNT Conditional.
- BR's minimum commitments are traced year by year: `$238.2M`, `$207.1M`, `$173.3M`, `$132.7M`,
  `$81.6M`, and `$35.5M` after year five. The `$868.4M` schedule differs from the reported `$868.5M`
  total by only `$0.1M` rounding; these operating costs remain inside post-cost cash conversion.
- STX conservatively deducts both `$45M` and `$75M` typed loss-contingency contexts. Their possible
  overlap is a named Conditional release condition.
- FSLR's `0.5% / 3% / 10%` cash-conversion margins are labeled FinSight assumptions, not reported
  contract/capacity facts. Claims include recorded litigation, possible excess loss, and unpaid capex.
- MPWR and PLTR retain reported SBC inside OCF and record exact H1 facts of `$94.282M` and
  `$466.801M`; both remain Conditional pending forward net-dilution/buyback normalization.
- Current acquisition consideration is not deducted twice after the acquired operations enter the
  consolidated issuer. No unsupported future acquisition growth is added; material new events invalidate.

## Independent challenge

Two disjoint `gpt-5.6-luna` reviewers challenged the candidate:

- High reasoning: source identity, cutoff, periods, units, shares, bridges, events, commitments,
  investment overlap, narrative provenance, and public safety.
- xhigh reasoning: model suitability, acquisitions, claims, SBC/dilution, cycle assumptions,
  sensitivities, classifications, and independent DCF replay.

Important findings repaired included PLTR/FTNT investment overlap, STX's wrapper diagnostic and
opaque claims, BR's untimed commitment schedule, FSLR's false source-like assumption label, CTSH's
appealed award treatment, and MPWR/PLTR SBC disclosure. Final disposition: **0 Critical / 0 Important**.
All 30 final scenarios replayed exactly.

## Determinism and real-consumer verification

- Source replay A/B: all ten reused, zero fetches, tree SHA-256
  `0decd5c0fb215a0ee13f6f3491aee66d44850a8a48a277ef670ca3e13138fe0c`
- Structural replay A/B: all ten reused, zero reparsing, tree SHA-256
  `414623663dcc3612c3793f121abd7e6bf60cbc0587aae5d815f55957ca9052ad`
- Final candidates H/I: 21/21 files byte-identical; report SHA-256
  `b0510f04733a03cd95538d03b284c202a4d6b3299ad6028380cac1c27a1105ab`
- Final candidate tree SHA-256:
  `2e8243c1ff5f4ced4d34465faeb1e49e3110f54dda189bdb80987c62f3f289f8`
- Focused Batch 30 tests: **11 passed**
- Complete backend suite after final code: **1,530 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed; no frontend code changed afterward
- Isolated cumulative catalog: **300 issuers** — 111 available / 180 conditional / 9 unavailable;
  artifact tree `86739247d5f90a85490f89eb6a32d6140112527b999cb6fad7f0725c23ffc50e`
- Real API: 300 list, 300 detail GET, 300 calculator GET/default parity; 291 numeric POST 200,
  9 unavailable POST 400, zero private leaks
- Exact detail/catalog parity: 300/300; forbidden serving imports: 0
- Calculator/API receipt SHA-256:
  `04ea8d952aed0bf147388053779030a0a5e8dc2a1bceaf0f8790a685b8793b66`
- Detail/import receipt SHA-256:
  `992c85459fb42489b42cb53c61841b134f8829f5cdadcbceff5166e812ff176a`
- Catalog manifest SHA-256:
  `309581ecc7912f8fcdad1fc4efa00e32553cd7ce9973214499f2b30bc6dc31a3`
- Pre-confirmation watchlist remains **181** — 172 Conditional / 9 Withheld, SHA-256
  `7b98db9dbd0c4b10c11b8e8b94cd3e016be860625c945b936d363b44d21da1c6`
- Automatic-withheld history remains **19**, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked serving catalogs, frontend public data, and frontend generated data remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-09-01. CTSH, ON, STX, FTNT, FSLR, MPWR, PLTR, and TEL entered the
Recovery Learning Watchlist as direct Conditional entries. The confirmed watchlist now contains
**189 companies** — 180 Conditional and 9 Withheld. TDY and BR were not added because they passed.
There are no Batch 30 Withheld companies, so no recovery attempt or withheld-register change is
needed. Batch 31, serving promotion, merge, push, and deployment remain outside scope.

Confirmed watchlist SHA-256:
`00f73edfc88db2ee7374473bb4abc31e9e94c13b0e85e896bac9714375b57f16`. The unchanged
withheld-register SHA-256 remains
`28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.
