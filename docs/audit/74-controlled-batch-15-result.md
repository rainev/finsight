# Controlled Universe Reset Batch 15 Initial Result

Status: **user confirmed on 2026-08-30**. Exactly the ten frozen Batch 15
Health Care issuers were processed at the 2026-08-14 valuation date. Initial processing changed no
bookkeeping. After confirmation, only the three direct Conditional issuers were added to the
Recovery Learning Watchlist. No recovery, cumulative-withheld-register mutation, tracked serving
promotion, Batch 16, merge, push, or deployment was performed.

## Result

- Pass: **4/10** — DVA, HSIC, DGX, MTD
- Conditional: **3/10** — RMD, WAT, CNC
- Withheld: **3/10** — LH, ISRG, ALGN
- Numeric: **7/10**, all Low reliability
- Cumulative after 150 processed issuers: **54 Pass / 87 Conditional / 9 Withheld**
- Cumulative numeric coverage: **141/150**
- Recovery Learning Watchlist: **93** after confirmation; the three direct Conditional issuers
  were added with recovery outcome `not_applicable`
- Cumulative withheld register: **10**, unchanged pending the authorized one recovery attempt

| Ticker | Outcome | Low | Base | High | Reliability | Controlling filing / period |
| --- | --- | ---: | ---: | ---: | --- | --- |
| LH | Withheld | — | — | — | — | `0000920148-26-000175` / 2026-06-30 |
| DVA | Pass | $112.80 | $255.50 | $421.66 | Low | `0000927066-26-000108` / 2026-06-30 |
| RMD | Conditional | $71.22 | $191.40 | $279.03 | Low | `0000943819-26-000047` / 2026-06-30 |
| HSIC | Pass | $9.81 | $41.49 | $67.19 | Low | `0001000228-26-000045` / 2026-06-27 |
| WAT | Conditional | $0.00 | $8.86 | $68.72 | Low | `0001193125-26-344691` / 2026-07-04 |
| DGX | Pass | $60.39 | $146.04 | $288.50 | Low | `0001022079-26-000070` / 2026-06-30 |
| ISRG | Withheld | — | — | — | — | `0001035267-26-000058` / 2026-06-30 |
| MTD | Pass | $379.86 | $596.17 | $863.87 | Low | `0001037646-26-000051` / 2026-06-30 |
| CNC | Conditional | $18.51 | $45.19 | $97.85 | Low | `0001071739-26-000153` / 2026-06-30 |
| ALGN | Withheld | — | — | — | — | `0001097149-26-000060` / 2026-06-30 |

Values are USD per-share baseline decision ranges, not predictions or recommendations. WAT's bear
case uses a limited-liability floor because the raw residual is negative; the private evidence
retains that negative raw value and does not pretend zero was a reported input.

## Frozen contract and source gate

The frozen order is LH, DVA, RMD, HSIC, WAT, DGX, ISRG, MTD, CNC, and ALGN. The manifest has eight
core and two boundary issuers, with no replacement or skipped ticker. Its SHA-256 is
`a14e038a09034820c62ffe938bbfebad181be06f0030388fd8c6f35bcc16f7a5`.

- SEC packets: 10/10 complete; RMD and ISRG reused complete packets and the other eight were
  captured only after cache preflight.
- Structural parsing: 10 attempted / 10 parsed / 0 failed; RMD and ISRG reused prior complete
  wrappers.
- Every controlling filing was filed by the 2026-08-14 cutoff.
- The frozen `RMD` issuer name remains `ResMed|`; CIK/ticker, not display-string equality, anchors
  source identity.
- WAT's controlling accession carries a filer prefix different from the issuer CIK, but its filing
  context/entity and frozen CIK reconcile to Waters. The identity exception is retained privately.
- Source replay A/B reused all ten with zero fetches and matched exactly:
  `0187c69ad433b140a6d9d0db325529136add95b777c99032d9ffe8e3d99e6460`.
- Structural replay A/B reused all ten and matched exactly:
  `e69c56053cdef2f8d7c3b09e30287508f817a43bb5984fef0f94f3131b2bbf34`.
- Protected tracked serving roots remained unchanged.

Structural wrapper top-level period diagnostics are not used for filing selection. Selection uses
the bound source receipt's filing/report dates and each fact's period.

## Outcome decisions

- **LH Withheld:** the filing says Labcorp entered a DOJ settlement on 2026-07-15 but gives no
  amount, reserve, payment schedule, or defensible upper bound. Subtracting zero or assuming
  immateriality would be invention. The ordinary diagnostics FCFF route remains reusable after the
  claim is bounded.
- **DVA Pass:** five-year cash history, cash/securities, debt/capital leases, $1.561416B redeemable
  NCI, $283.118M other NCI, and $39.463M acquisition obligations reconcile. The historical range
  retains the 2025 cyber-related collection disruption and recovery.
- **RMD Conditional:** MatrixCare was held for sale, not closed, at the cutoff. The $490M expected
  proceeds are not credited. Its approximately $220M annual revenue, $28M operating profit,
  $457.386M fair value, and current acquisitions are material but finite, so the standalone range
  is numeric and capped Low.
- **HSIC Pass:** current/long-term financing, $906M temporary equity, $660M nonredeemable NCI, and
  $58M contingent consideration are separated and source bounded. Operating leases remain post-rent
  operating items rather than a second debt deduction.
- **WAT Conditional:** the $13B BDS combination issued 38.542M shares and changed scale. The model
  uses the reliable 98.248M cover count rather than the parser's 1,000× weighted-share scale error.
  Revenue is anchored to 2 × reported $3.185B pro-forma H1 revenue; bear cash conversion is reported
  H1 OCF less productive-asset spend divided by reported revenue. Base/bull stay below the lowest
  comparable pre-combination annual margin, and the $201M pro-forma net loss is retained as a
  conservative constraint.
- **DGX Pass:** current cash, debt, NCI, redeemable NCI, and contingent consideration reconcile.
  Current malpractice/legal reserves remain operating liabilities already represented in cash
  conversion; stale 2020/2021 claim facts are not substituted as current claims.
- **ISRG Withheld:** the debt-free owner-cash route and $8.6255B aggregate cash/securities fact are
  valid, but current product-liability disclosures say claims may exceed accruals and no excess-loss
  range can be estimated.
- **MTD Pass:** stable history and current cash/debt reconcile. The cover and dimensioned common
  share facts agree at 20.036559M; the conflicting unqualified 21.683802M tag is retained as an
  extraction diagnostic but excluded. H1 diluted weighted shares supply the conservative bear
  denominator.
- **CNC Conditional:** an equity-level managed-care residual-income route keeps medical claims,
  member funds, debt, investments, regulated capital, and NCI inside common earnings/equity. The
  2025 loss is normalized with the source-reported $6.723B noncash goodwill impairment, leaving
  $52M residual parent earnings. Annualized H1 removes the after-tax $481M favorable prior-year
  risk-adjustment item. Claims/capital/PDR uncertainty keeps the result Low.
- **ALGN Withheld:** owner cash is usable, but the filing cannot estimate current legal/IP losses;
  the EU competition investigation may produce substantial fines and follow-on claims. Recovery
  must also reconcile the material private-investment balance without treating unused revolver
  capacity as debt.

## Independent challenge and repairs

The Luna xhigh challenge reproduced the routes and initially found two Critical and five Important
issues. All were repaired:

- ISRG and ALGN moved from Pass to Withheld for genuinely unbounded claims.
- ISRG cash/securities moved from an overlapping cash-plus-AFS sum to the $8.6255B aggregate fact.
- WAT's cash-conversion range was bound to current combined cash, pro-forma revenue/loss, and
  pre-combination history rather than unsupported round margins.
- DVA's $39.463M acquisition obligation was included once.
- CNC's 2025 impairment and current risk-adjustment benefit were explicitly normalized.
- MTD's share tags were reconciled to matching cover/dimensioned counts.

The exact repaired-candidate recheck found no remaining Critical or Important issue.

Two Luna subagents were used under the efficiency workflow: Zeno (`gpt-5.6-luna`, High) inventoried
source/event/claim evidence; Archimedes (`gpt-5.6-luna`, xhigh) challenged the exact model candidate.
The Sol parent performed implementation, arithmetic repair, deterministic replay, tests, catalog,
and real API verification.

## Determinism, tests, build, and real API

- Final candidate A/B full-tree SHA-256:
  `35bf55fa84100f5408db16efa15bf6e926e47ed5d463fb73a77be1df3dad98a6`
- Generated-private tree SHA-256:
  `c1652e272360154e6d1bd84944f6abdcf29a7fd70481467466befb711aa68500`
- Staged-public tree SHA-256:
  `9c95c3c3571d400d747c6c49bcea351da3879235fac2cd67cb1d0e8debcabdb6`
- Focused Batch 15 tests: `5 passed`
- Full backend suite: `1,514 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- Isolated cumulative catalog: `150` artifacts, Batches 01–15
- Catalog availability: `54 available / 87 conditional / 9 unavailable`
- Catalog publication: `141 review-required / 9 withheld`
- Catalog artifact-tree SHA-256:
  `f685d8eac1999dcc925255f9cac7bbe9443b1f733a4f8d896757b60e489a68ec`
- Real localhost FastAPI list: HTTP 200, exact count 150
- Detail/catalog parity: 150/150; exact Batch 15 staged parity: 10/10
- Calculator GET parity: 150/150
- Batch 15 numeric routes: six operating-family and one managed-care equity-earnings family
- Calculator default POST parity: 141/141 numeric HTTP 200; nine Withheld HTTP 400
- Private leaks: 0
- API receipt SHA-256:
  `4d3c6171cc72273c5e3b1283035294bfb16b90c35d3886f0ec80c9f5e00a63c6`

The API used an isolated untracked catalog and local auth harness with `save=false`. Arelle remained
an offline extraction worker and was not loaded by the serving path. This verifies real HTTP
list/detail/calculator behavior, not production authentication, persistence, promotion, or deploy.

## Confirmation and recovery gate

The user replied `y` and confirmed the initial result on 2026-08-30. RMD, WAT, and CNC were added
to the Recovery Learning Watchlist as direct Conditional results with recovery outcome
`not_applicable`. LH, ISRG, and ALGN remain outside the watchlist and cumulative withheld register
until their separately authorized one recovery attempt is complete.

- Watchlist: 93 entries — 87 Conditional / 6 post-recovery Withheld
- Watchlist SHA-256: `0c0420a158e3ba8f464b28dd5f2ca65ab2aa97561e23a03d5e8821b79d6e929d`
- Cumulative withheld register: unchanged at ten entries, SHA-256
  `0205878089044e64002b8e181821939c266681e5258b882d2749ef3d068ae109`
- Focused Batch 15/watchlist/withheld confirmation checks: `11 passed`

The next valid signal is:

`Attempt recovery for Batch 15 withheld companies.`

Recovery update: the authorized one-attempt recovery is complete in
[Audit 76](76-batch-15-recovery-result.md). LH, ISRG, and ALGN remain Withheld and have been added
to both post-recovery registers; final Batch 15 remains Pass 4 / Conditional 3 / Withheld 3.

Do not start Batch 16, register the three initial Withheld companies, promote, merge, push, or
deploy before the recovery gate.
