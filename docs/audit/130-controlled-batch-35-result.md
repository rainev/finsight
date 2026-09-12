# Controlled Universe Reset Batch 35 Result

Date: 2026-09-04
Status: **user-confirmed on 2026-09-04**

## Outcome

The exact frozen denominator was processed with cutoff-safe SEC filings, period-aligned company
history, issuer-suitable equity-level or operating models, two independent challenges, two
byte-identical final replays, the complete backend suite, the frontend production build, and a real
local API over an isolated 350-company catalog.

- Pass: **0/10**
- Conditional: **10/10 — WFC, WMB, AON, SCHW, GL, AJG, PNC, RJF, CFG, JKHY**
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **10 Low**

| Ticker | Outcome | Low | Base | High | Why it remains Conditional |
| --- | --- | ---: | ---: | ---: | --- |
| WFC | Conditional | $38.90 | $59.47 | $79.37 | Credit, funding, regulatory capital, and preferred claims remain materially scenario-dependent. |
| WMB | Conditional | $0.00 | $17.71 | $44.06 | Commodity/project timing, heavy capex, and leverage create a valid negative raw bear residual; public bear is floored at zero. |
| AON | Conditional | $47.83 | $78.04 | $109.60 | Acquisition cash and contingent consideration are material and not yet separated into recurring versus exceptional reinvestment. |
| SCHW | Conditional | $19.69 | $32.16 | $45.13 | Client-cash economics, preferred claims, capital, and a pre-cutoff $2.6B note issuance remain material. |
| GL | Conditional | $62.86 | $96.50 | $129.36 | Life-insurance mortality, reserves, investment marks, and regulatory capital need specialist bounds before Pass. |
| AJG | Conditional | $64.31 | $104.22 | $143.93 | Acquisition cash and earnout exposure are material and not yet normalized as recurring versus exceptional. |
| PNC | Conditional | $100.88 | $156.58 | $211.08 | Bank capital, credit/funding assumptions, the preferred claim, and a pre-cutoff $2.0B note issuance remain material. |
| RJF | Conditional | $51.15 | $81.35 | $112.13 | Brokerage market/client-asset sensitivity and capital remain material. |
| CFG | Conditional | $35.14 | $54.05 | $72.02 | Regional-bank credit, deposit pricing, securities marks, capital, and preferred claims remain material. |
| JKHY | Conditional | $26.91 | $42.97 | $59.75 | It is the closest Pass candidate, but the latest cutoff-safe 10-Q is March 31 and acquisition/recurring-revenue evidence still needs an explicit release check. |

No company is withheld: every company has a finite, ordered range and a positive base value. The
zero WMB bear case is a limited-liability display floor; its negative raw residual remains private
and traceable.

## Important repairs made before acceptance

- Historical equity now uses each issuer's actual audited fiscal-year end, including September 30
  for RJF and June 30 for JKHY, rather than assuming December 31.
- Beginning and current preferred claims are period-specific: WFC `$17.376B/$16.116B`, SCHW
  `$6.871B/$6.315B`, and RJF `$79M/$0`.
- GL's reported zero preferred shares and zero carrying value are treated as explicit absence; the
  draft's synthetic 1–3% claim was removed.
- PNC's rounded zero par-value line is not treated as no claim. The model uses the filing's `$5.879B`
  preferred stock plus related surplus, derives the prior `$5.760B` after the reported `$119M`
  FirstBank preferred issuance, and binds the table to its accession, URL, locator, document hash,
  and package hash.
- WMB deducts `$2.178B` NCI plus `$35M` preferred stock exactly once. Unreported investments are
  explicitly excluded; no unavailable value is converted to zero.

## Independent challenge

Two independent reviews challenged sources, periods, preferred treatment, economic model choice,
event handling, arithmetic, and public safety. The draft findings on GL, period-specific preferred
claims, PNC provenance/classification, and WMB's bridge were repaired. Final disposition:
**0 Critical / 0 Important**. All 30 scenarios replay through the shared calculators exactly.

## Determinism and real-consumer verification

- Final G/H replays: **21/21 files byte-identical**; full tree
  `631e39b65620b0b5e0ac24df94b9e75e7f8d0f2efb3471496af3e317e9f7c72e`
- Final report SHA-256:
  `4d389d4e3853135f970340a14ea64c0c32ecc1039a4a36de8ba1d052ea2ee2a6`
- Focused Batch 35 tests: **8 passed**
- Complete backend suite: **1,594 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated cumulative catalog: **350** — 116 available / 224 conditional / 10 unavailable;
  artifact tree `53422f51f4aa84081a1c290cff6552d9fc32bd9119e642a70d3f5cd83d4c1ca4`
- Real local API: **350 list, 350 detail, 350 calculator/default parity; zero private leaks**
- Exact list parity: true; exact detail parity: **350/350**; forbidden serving imports: **0**
- Calculator/API receipt SHA-256:
  `8abb3a75e20a88f2a5f8c2ec77ff781d4f4fd2595dc8e0f7b628f31f927e300d`
- Exact-list/detail/import receipt SHA-256:
  `a57dbdb7579a5728b7016b01e9065c9219fd186869cc676f455db42dd8a6f4a2`
- Catalog manifest SHA-256:
  `18b0288995b4145977db18b9d125de1c262346ed0ccd84131ad67600e724ebad`

The first full-suite command was run from the backend subdirectory and failed only because legacy
tests resolve evidence paths from the repository root; the correctly rooted complete run passed as
reported above. This command-context mistake did not change code or evidence.

## Confirmation boundary

Existing tracked serving artifacts and the withheld register remain unchanged. The user confirmed
this exact result with `y`; all ten Conditional companies were added to the Recovery Learning
Watchlist, taking it from 224 to **234 entries** — 224 Conditional and 10 Withheld. Updated
watchlist SHA-256: `0107c2acea1249c130790a73ead2f736c2bdb07c8bd49aa00967b048f771e80b`.

Recovery, Batch 36, tracked serving promotion, merge, push, and deployment remain separate actions.
