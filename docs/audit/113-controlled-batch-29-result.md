# Controlled Universe Reset Batch 29 Initial Result

Date: 2026-09-01  
Status: **user-confirmed on 2026-09-01**

## Outcome

- Pass: **3/10** — CIEN, NTAP, VRSN
- Conditional: **7/10** — TRMB, ROP, SNPS, INTU, NVDA, FFIV, AKAM
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Reliability | Simple reason |
| --- | --- | ---: | ---: | ---: | --- | --- |
| TRMB | Conditional | $10.35 | $23.56 | $49.54 | Low | Recent acquisition, goodwill impairment, investments, and purchase commitments make history provisional |
| ROP | Conditional | $213.28 | $411.55 | $668.06 | Low | Indicor is still an unclosed sale; its stake/proceeds require a separate governed range |
| SNPS | Conditional | $83.46 | $209.69 | $367.39 | Low | The $34.9B Ansys acquisition, restructuring, debt, and pending Processor IP state remain material |
| INTU | Conditional | $260.07 | $490.06 | $838.66 | Low | Customer funds reconcile, but business-loan reinvestment, restructuring, and legal proceedings remain material |
| CIEN | Pass | $14.15 | $67.71 | $135.95 | Low | The down-cycle is present in history and the non-overlapping cash, debt, lease, warranty, and share bridge reconciles |
| NTAP | Pass | $64.18 | $116.20 | $186.73 | Low | Five-year storage cash history and the cash/securities/debt/share bridge reconcile; commitments fit operating liquidity |
| VRSN | Pass | $115.92 | $187.81 | $277.57 | Low | Recurring registry cash and the post-July-redemption cash/debt state reconcile |
| NVDA | Conditional | $35.46 | $103.55 | $190.45 | Low | Exceptional cash is offset by very large supply/cloud/investment/lease commitments, volatile investments, and legal/export risk |
| FFIV | Conditional | $156.90 | $256.68 | $378.18 | Low | Operating cash is strong, but the cyber incident has possible claims with no filed total loss range |
| AKAM | Conditional | $42.93 | $89.66 | $142.10 | Low | LayerX closed after quarter-end while new convertible debt, cloud capex, and dilution remain material |

These are baseline decision ranges, not predictions or recommendations. Every range is finite,
ordered, and has a positive base. No unavailable value was replaced with zero.

## Controlling sources

| Ticker | Accession | Filed | Report period |
| --- | --- | --- | --- |
| TRMB | 0000864749-26-000108 | 2026-08-12 | 2026-07-03 |
| ROP | 0000882835-26-000036 | 2026-07-31 | 2026-06-30 |
| SNPS | 0000883241-26-000018 | 2026-05-27 | 2026-04-30 |
| INTU | 0000896878-26-000025 | 2026-05-20 | 2026-04-30 |
| CIEN | 0001628280-26-040767 | 2026-06-04 | 2026-05-02 |
| NTAP | 0001193125-26-259683 | 2026-06-05 | 2026-04-24 |
| VRSN | 0001014473-26-000028 | 2026-07-23 | 2026-06-30 |
| NVDA | 0001045810-26-000052 | 2026-05-20 | 2026-04-26 |
| FFIV | 0001048695-26-000067 | 2026-08-06 | 2026-06-30 |
| AKAM | 0001086222-26-000086 | 2026-08-07 | 2026-06-30 |

SNPS, INTU, and NVDA source packets/packages were reused from validated difficult-106 evidence;
seven packets were captured. The initial long structural pass produced six complete new wrappers
before ending without a summary. The resumed immutable pass reused those six plus SNPS/INTU/NVDA
and captured only VRSN, FFIV, and AKAM. Final cache-only A/B replays reused all ten with zero
fetches or reparsing. Every malformed wrapper-level diagnostic date is recorded as
`used_for_selection: false`; filing receipt dates and fact periods control.

## Load-bearing treatments

- ROP includes its Indicor stake once using a $1.3B/$1.5461B/$1.7922B nonoperating range anchored
  by expected pre-tax proceeds and current Level-3 carrying value. Capitalized software is deducted
  as reinvestment. Expected proceeds are not treated as realized cash.
- INTU excludes $7.760B of exactly matched customer assets/payables. Issuer cash/investments are
  $6.956B and debt is $6.162B. Business-loan reinvestment reduces bear/base/bull cash by
  $554.667M/$416M/$0; unquantified legal matters remain `None`, never zero.
- CIEN uses $1.40294B of non-overlapping cash/current/noncurrent investments. The $468.377M
  aggregate AFS fact overlaps those components and is not added again.
- VRSN subtracts the July 20 $550M redemption from cash and removes the $549.3M current carrying
  debt, leaving $1.7851B noncurrent debt.
- NVDA ranges marketable/nonmarketable investments, deducts Groq consideration, recorded tax
  exposure, contingent investment commitments, and net guarantee exposure, and applies a timed PV
  reserve to $32.4B of future not-commenced leases. The $2.3B infrastructure-fund maximum exposure
  is explicitly a subset of already modeled invested/committed amounts. Operating supply/cloud
  commitments remain inside post-cost cash conversion rather than being deducted as debt.
- FFIV uses the approved reported-operations legal-tail policy: response costs and insurance
  recoveries stay in history; unknown future cyber claims remain outside the range and are not
  assumed zero.
- AKAM deducts approximate LayerX cash consideration once and uses the latest-quarter diluted-share
  ceiling while keeping convertible hedge/warrant uncertainty Conditional.

## Independent challenge

Two disjoint `gpt-5.6-luna` reviewers were used under the FinSight efficiency workflow:

- High reasoning: identity, cutoff, accessions, periods, units, shares, cache reuse, bridges,
  event facts, and narrative-document provenance.
- xhigh reasoning: model choice, classifications, acquisitions/divestitures, commitment treatment,
  reinvestment, claims, DCF arithmetic, dilution, and calculator behavior.

Important findings repaired included ROP's Indicor omission and software reinvestment, INTU's
customer-fund/loan treatment, CIEN's overlapping investments, VRSN's completed redemption, SNPS's
net debt/latest-quarter shares, NVDA's commitments/tax/guarantee/lease/VIE treatment, FFIV's legal
tail, AKAM dilution, and document-hash lineage for narrative facts. Final disposition:
**0 Critical / 0 Important**. Both reviewers independently accepted the final repaired state, and
the model reviewer replayed all 30 final I/J DCF scenarios exactly.

## Determinism and verification

- Source replay A/B: all ten reused, zero fetches, byte-identical hash
  `22c9bdc265629f8daf9f94951d2b3fd9b453be88323d9600f59e22159ca56db3`
- Structural replay A/B: all ten reused, zero reparsing, byte-identical hash
  `333a495273b1284bb752d17c85555337894a2d9f3e28d879fd01ce5ae52780c9`
- Final candidate I/J: 21/21 files byte-identical; report SHA-256
  `cf93d96b67d6dba9012f366cbf60d941cb8235aa5d80bdb6ec122cea7cb61ede`
- Final candidate tree: `abcec8ec9a8efd136971676bec8062148183e2d2ed4291bb6ca2555ac229f3ea`
- Focused Batch 29 tests: **9 passed**
- Complete backend suite after final code: **1,519 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated cumulative catalog: **290 issuers** — 109 available / 172 conditional / 9 unavailable;
  artifact tree `654312ecf4ce85efe10944afe8f0c4ed2ec05238558badc728f13c28d0265a8a`
- Real API: 290 list, 290 detail GET, 290 calculator GET/default parity; 281 numeric POST 200,
  9 unavailable POST 400, zero private leaks
- Exact detail/catalog parity: 290/290; forbidden serving imports: 0
- Calculator/API receipt SHA-256:
  `f2198bfb2c13d00f1de228f401f4ef59d36228c3024a452a294b4c60a65d1da8`
- Detail/import receipt SHA-256:
  `ce00ab4ac1b2ff8dd436b8be07b23b67e4bfe5253a3afa6b0fad78ff86805598`
- Catalog manifest SHA-256:
  `28da7d73f6495dae79bec672d540fdb116e31e352bb3ec133ba8473243c8bc13`
- Pre-confirmation watchlist remains 174 (165 Conditional / 9 Withheld), SHA-256
  `0f0f657b7ae4c802b9c4142f6173d0b5851730f11e35e8c67c4b4e354a0d22d9`
- Automatic-withheld history remains 19, SHA-256
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`
- Tracked protected roots remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-09-01. TRMB, ROP, SNPS, INTU, NVDA, FFIV, and AKAM entered the
Recovery Learning Watchlist as direct Conditional entries. The confirmed watchlist now contains
**181 companies** — 172 Conditional and 9 Withheld. CIEN, NTAP, and VRSN were not added because
they passed. There are no Batch 29 Withheld companies, so no recovery attempt or withheld-register
change is needed. Batch 30, serving promotion, merge, push, and deployment remain outside scope.

Confirmed watchlist SHA-256:
`7b98db9dbd0c4b10c11b8e8b94cd3e016be860625c945b936d363b44d21da1c6`. The unchanged
withheld-register SHA-256 remains
`28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`.
