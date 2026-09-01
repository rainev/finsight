# Batch 16 Whole-Batch Baseline Repair Result

Status: **user confirmed on 2026-08-30**. The user explicitly authorized an
exceptional whole-Batch-16 repair after the one automatic recovery attempt. The prior attempt and
[Audit 80](80-batch-16-recovery-result.md) remain preserved; this repair does not reset that attempt.
No Batch 17, tracked serving promotion, merge, push, or deployment was performed.

## Outcome

- Attempted: **10/10** — A, DXCM, EW, CRL, ZBH, COR, PODD, ELV, VEEV, IQV
- Final Pass: **3/10** — PODD, VEEV, IQV
- Final Conditional: **7/10** — A, DXCM, EW, CRL, ZBH, COR, ELV
- Final Withheld: **0/10**
- Final numeric coverage: **10/10**
- Newly numeric: **6/6** — DXCM, EW, CRL, ZBH, COR, ELV
- Upgraded Conditional to Pass: **PODD**
- Cumulative through 160 issuers: **57 Pass / 94 Conditional / 9 Withheld**
- Cumulative numeric coverage: **151/160**

All ten results remain Low reliability because their scenario widths are material. The six newly
numeric results are not presented as complete lawsuit valuations. They value source-reported
going-concern operations and recorded claims. Each unknown legal tail remains `None` privately,
is never replaced with zero or a guessed haircut, and is publicly disclosed as capable of moving
actual value outside the range.

## Company results

| Ticker | Result | Low | Base | High | Practical treatment |
| --- | --- | ---: | ---: | ---: | --- |
| A | Conditional Low | $33.37 | $65.73 | $103.86 | Unchanged pre-Biocare standalone value; pending acquisition remains separate |
| DXCM | Conditional Low | $16.47 | $34.59 | $69.89 | Five-year diabetes-device cash model; current securities/derivative/device claims outside range |
| EW | Conditional Low | $22.72 | $42.40 | $58.05 | Post-Autus medtech cash model; recorded reserve and governed contingent consideration included |
| CRL | Conditional Low | $21.25 | $69.80 | $134.87 | Five-year life-sciences-services cash model; securities/derivative tail outside range |
| ZBH | Conditional Low | $36.93 | $77.99 | $123.17 | Current interest extraction repaired; debt, NCI, litigation, and contingent consideration included |
| COR | Conditional Low | $110.76 | $205.76 | $375.78 | Full $4.2B opioid accrual and NCI deducted once; claims outside the schedule disclosed |
| PODD | Pass Low | $20.95 | $68.16 | $133.34 | Filing says proceedings are not expected to be materially adverse and Hu loss is not probable |
| ELV | Conditional Low | $121.67 | $231.20 | $419.52 | Managed-care residual income; bounded CMS matter reflected, separate DOJ/provider tail disclosed |
| VEEV | Pass Low | $139.90 | $202.84 | $285.90 | Unchanged debt-free health-cloud owner cash |
| IQV | Pass Low | $58.07 | $153.56 | $230.18 | Unchanged health-data-services faded cash model |

## Important repairs made during challenge

### Scoped ZBH interest extraction

ZBH reports current interest through `InterestIncomeExpenseNet`. Adding that concept globally made
the normalizer select different interest paths for previously confirmed YUM and SYY, and the full
suite failed. The global change was removed. The concept is now enabled only for ZBH's repair path.
TTM interest is source reconstructed as `−$292.8M − $141.7M + $145.5M = −$289.0M`.

### EW trace corrections

- The $20.4M interest input is explicitly labeled a FY2025 carry-forward estimate, not TTM.
- The $70M base Autus contingent-consideration value is labeled the governed midpoint between the
  filed $7.5M current liability and $132.5M maximum.
- A separate $70M MedicalDeviceCompany equity-issued fact is recorded as unused for the Autus
  midpoint; it is not misrepresented as contingent consideration.

### PODD classification

The official 10-Q states that current legal proceedings are not expected to have a material adverse
effect and that a Hu loss is not probable, so no accrual was recorded. The repair upgrades PODD to
Pass while retaining Low reliability. Its zero accrual remains a reported accounting fact; ultimate
loss remains unknown rather than being estimated as zero.

## Independent challenge

Three independent lenses challenged the exact repaired candidate:

- `gpt-5.6-luna`, High — DXCM/EW/CRL source identity, TTM/history arithmetic, bridges, shares,
  recorded claims, and legal-tail disclosure. Two EW Important findings were repaired; final
  candidate-g recheck found none remaining.
- `gpt-5.6-luna`, xhigh — ZBH/COR/ELV arithmetic, model suitability, sensitivity direction,
  recorded-claim treatment, ZBH interest scoping, and ELV equity routing. No Critical or Important
  finding remained.
- `gpt-5.6-luna`, High — A/PODD/VEEV/IQV classification and values, whole-batch API/calculator
  family consistency, public safety, and attempt semantics. No Critical or Important finding.

The reviewers' earlier strict-policy objection is preserved: these ranges do not bound every legal
outcome. Under the user's baseline-first policy, that is resolved by Conditional/Low classification,
an explicit range scope, `None` for unknown loss, and a public outside-range warning—not by claiming
the legal risk disappeared.

## Determinism and automated verification

- Candidate-g/candidate-h full-tree SHA-256:
  `d0a28b103eea30dd57d3c3bf0be5efa83e48ab4dfcb23191b40a9e2c4bf288d8`
- Generated-private tree SHA-256:
  `2df0217080a06ceb635e06db7de401ec3e38fd99e233cbf60fbb2a43e3799226`
- Staged-public tree SHA-256:
  `cb7f525f2c55210fa7e578fda672488b42b5280b625c9a8d0db23a38b536be57`
- Whole-repair report SHA-256:
  `379a52f21fd648032618252ec0a766de749dfc6ac3a812dc34b2a7a664ba5383`
- Final focused repair/watchlist/withheld/catalog checks: `22 passed, 1 warning`
- Complete backend suite: `1,537 passed, 3 skipped, 1 warning`
- Frontend production build: passed (`1,694` modules transformed)
- `git diff --check`: passed

## Real consumer path

- Isolated cumulative catalog: `160` artifacts, Batches 01–16
- Availability: `57 available / 94 conditional / 9 unavailable`
- Publication: `151 review-required / 9 withheld`
- Catalog artifact-tree SHA-256:
  `af92e2591472d848f4d4243dd3eb3f80e01ec6dcfcea4941ce9c783d84afaad4`
- Real localhost FastAPI list: HTTP 200, exact count 160
- Detail/catalog parity: 160/160; exact repaired Batch 16 parity: 10/10
- Calculator GET parity: 160/160
- Calculator POST: 151 numeric HTTP 200; nine unavailable HTTP 400
- Batch 16 calculator families: nine operating / one equity-earnings
- Private leaks: 0
- API receipt SHA-256:
  `96ae789928943c6e6ea257db4e3ee74ce729d3c9b97fe14deeca1582dc52bd41`

The API used an isolated untracked catalog, local test-only auth harness, and `save=false`. Arelle
remained outside the serving process. Tracked serving roots remained unchanged.

## Bookkeeping and confirmation gate

- Recovery Learning Watchlist: **103** — 94 current Conditional / 9 post-recovery Withheld
- PODD was removed because it is now fully recovered as Pass.
- The six newly numeric companies remain bookmarked as Conditional because their legal tails remain
  outside the reported-operations ranges.
- Watchlist SHA-256:
  `6d685d784ba4c051891ead366a01f5c356b53e84e3234e8adc64bca2d57254e7`
- Cumulative automatic-withheld history: **19**; unchanged so the consumed Batch 16 recovery attempt
  and Audit 80 are not erased.
- Withheld-history SHA-256:
  `28bcfdd2985f3f3d87320e9e780aac630923510d0e46c614d9cfb5035e19f3ec`

The user replied `y` and confirmed this exact whole-batch repair on 2026-08-30. Batch 17 remains
untouched and requires the separate signal `Start Universe Reset Batch 17`.
