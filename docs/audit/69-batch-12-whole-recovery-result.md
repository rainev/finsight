# Batch 12 Whole-Batch Recovery Result

Status: **user confirmed on 2026-08-28**. The user authorized one recovery
attempt for all ten Batch 12 issuers after rejecting the usefulness of several initial values.
The attempt used only the frozen 2026-08-14 evidence, preserved candidate-i as immutable
comparison evidence, and used no stock price, analyst target, new network fetch, serving promotion,
Batch 13 work, merge, push, or deployment.

## Outcome

- Recovery attempts consumed: **10/10**, exactly one per issuer
- Final Pass: **0/10**
- Final Conditional: **9/10** — ABT, BAX, BDX, BMY, RVTY, HUM, LLY, CVS, WST
- Final Withheld: **1/10** — UHS
- Final numeric: **9/10**, all Low reliability
- Cumulative after 120 issuers: **47 Pass / 67 Conditional / 6 Withheld**
- Cumulative numeric coverage: **114/120**

The statuses did not change, but all nine numeric values were re-underwritten with issuer-specific
models and source-complete claims/events.

| Ticker | Initial range | Recovery range | Base change | Final status |
| --- | ---: | ---: | ---: | --- |
| ABT | $20.75 / $42.13 / $68.16 | $29.69 / $58.21 / $89.65 | +$16.08 / +38.2% | Conditional |
| BAX | $0.00 / $6.87 / $23.60 | $0.00 / $8.55 / $27.12 | +$1.67 / +24.4% | Conditional |
| BDX | $37.78 / $89.98 / $161.39 | $38.33 / $97.90 / $170.63 | +$7.92 / +8.8% | Conditional |
| BMY | $39.97 / $60.49 / $95.54 | $39.98 / $69.49 / $108.20 | +$9.00 / +14.9% | Conditional |
| RVTY | $17.05 / $39.34 / $73.53 | $23.95 / $47.46 / $79.27 | +$8.13 / +20.7% | Conditional |
| HUM | $49.06 / $124.31 / $254.86 | $79.52 / $159.45 / $278.23 | +$35.14 / +28.3% | Conditional |
| LLY | $41.47 / $149.70 / $279.32 | $68.60 / $288.68 / $609.33 | +$138.99 / +92.8% | Conditional |
| CVS | $12.94 / $25.93 / $57.27 | $26.70 / $41.34 / $74.10 | +$15.41 / +59.4% | Conditional |
| WST | $55.15 / $79.81 / $114.54 | $56.57 / $87.67 / $127.72 | +$7.86 / +9.8% | Conditional |
| UHS | — | — | — | Withheld |

Values are USD per-share decision ranges, not price targets, recommendations, or probability-
weighted forecasts. BAX's raw bear residual remains negative and is preserved privately; the
published zero is the governed limited-liability floor.

## Why the values changed

The initial source/arithmetic layer was correct, but its model policy was too generic. Audit 68
showed that seven operating issuers shared a constant-growth five-year DCF with a blanket
3%/4%/5% growth cap and 0%/1%/2% terminal growth, while HUM/CVS used unanchored fixed earnings
multiples.

Recovery reused the existing engines:

- eight-year `EnterpriseCashFlowState` forecasts with explicit growth fade and terminal growth no
  higher than 2.5% for ABT, BAX, BDX, BMY, RVTY, LLY, and WST;
- common-equity residual income with clean-surplus DDM reconciliation for HUM and CVS;
- issuer-specific current scale, downside, claims, transactions, payout, ROE, and required-return
  states, always separated from reported facts.

LLY is the largest change. The initial 4% base growth was disconnected from its 25.78%
source-linked historical median and 51.2% current H1 growth. Recovery uses 10%/18%/25% explicit
growth, all materially below current/history evidence, fading over eight years to 1%/2%/2.5%.

## Source and event corrections

- **ABT:** starting scale is exactly 2 × filed $24.5B pro-forma combined H1 revenue. Historical
  cash conversion—not pro-forma pretax income—supplies cash margins. Claims total $1.425B:
  $652M NCI + $263M acquisition contingent consideration + $510M recorded legal/environmental
  accrual.
- **BAX:** claims total $105M: existing $10M contingent consideration + $43M separation
  indemnification + $52M Vantive capex-reimbursement liability. The $28M retained guarantees are
  Carlyle-indemnified and not added. The 21% practical tax policy remains explicit.
- **BDX:** the completed spin's $3.857B distribution is not added twice. A $1.6B recorded
  product-liability/legal accrual is deducted once; $181M supplier finance remains in AP/OCF.
- **BMY:** claims total $1.557B: $607M CVR + $950M fixed Hengrui payments. The $14.3B contingent
  milestone maximum remains a separate unweighted event surface. A -3% base-business downside is
  present in the bear state.
- **RVTY:** gross $3.2222B debt, $8M ACD claim, $72M acquisition, and restructuring evidence stay
  source-bound. The $32.818M restructuring reserve remains operating in OCF/history.
- **HUM/CVS:** reported parent equity, beginning/ending equity, common earnings, and annualized H1
  payout anchor residual income. Deposits/claims/member funds/debt remain inside the equity object;
  no EV debt bridge is applied.
- **LLY:** claims total $4.518B: existing $2.518B contingent consideration + approximately $2.0B
  paid for July acquisitions. The three-company $3.9B maximum and pending $2.8B AtaiBeckley remain
  separate event surfaces; no acquired earnings or invented financing is added.
- **WST:** $136M SmartDose proceeds remain included once. Because history still includes the sold
  product, no invented continuing-cash adjustment is made and the result remains Conditional.
- **UHS:** recovery remains Withheld. A finite $188M Ireland reserve does not reconstruct the
  combined post-period state after Provo Canyon license revocations/patient discharges, new CMG
  management and financial responsibility, and pending $835M debt-financed Talkspace.

Every private attempt records the exact source-packet, package, receipt, and structural-filing
hashes, the approved initial range, attempt number one, method, and explicit confirmation that no
market price or analyst target was used.

## Independent challenge

Three independent Luna XHigh reviewers challenged disjoint scopes: source/period/unit/share/
claim/event completeness; economic model/calibration/sensitivity; and runner/public/bookkeeping/API
mechanics. Sol independently rechecked all load-bearing facts and reconciled disagreements.

Resolved findings included ABT's pro-forma scale and legal accrual, BAX retained separation
claims, BDX's $1.6B legal accrual, BMY fixed Hengrui payments, LLY July/pending transaction
surfaces, UHS's additional post-period operating blockers, HUM/CVS calculator routing, stale
bridge prose, candidate-i hash pinning, derived report counts, and Batch-12-scoped recovery
bookkeeping semantics. Final verdict: **PASS with no Critical or Important finding**.

Minor caveats remain explicit: pro-forma ABT scale is not a forecast; BDX legal payout timing is
not separately modeled; BMY/LLY contingent pipeline outcomes are not probability-weighted;
HUM/CVS terminal ROE and payout remain policy inputs; WST lacks post-sale annual history; public
scenario/sensitivity arrays remain empty while private schedules contain the verified directions;
and some inherited structural rows display `filed: null` while their controlling receipt retains
the filed date.

## Bookkeeping

All ten Batch 12 issuers were added to the Recovery Learning Watchlist because none became a
source-bounded Pass. Only still-Withheld UHS was added to the cumulative withheld register.

- Recovery Learning Watchlist: **73** — 67 Conditional / 6 Withheld
- Watchlist SHA-256: `900c35dbf5b3c1c182d2a197bdae9125ab66c12d2a675ceb300a76a2f54811d4`
- Cumulative withheld register: **10** entries
- Withheld-register SHA-256: `0205878089044e64002b8e181821939c266681e5258b882d2749ef3d068ae109`
- Bookkeeping receipt SHA-256: `0d2452aae85db4ef9d9b8988126db291870d90e94ce24913bedf5e3ea114345e`

The writer required the exact pre-recovery hashes, rejected duplicates, sorted by batch/CIK,
validated both schemas before writing, and preserved tracked serving hashes.

## Determinism, tests, build, and real API

- Final candidate-g/h full-tree SHA-256:
  `719299168195b46e8a3f13dd32b5d69ed95f874b89037884071cc227f48ac870`
- Generated-private tree SHA-256:
  `a5f4e61eaaaf54a8c565bb97e4aa9aae37ca4cb46c5211414220f3dd2818b198`
- Staged-public tree SHA-256:
  `82799a6e60c9299149115ec4c8966147da42240c97525716d00e5f6cc8782f14`
- Recovery report SHA-256:
  `d02eb935ade868f74b17f1c72056a9017b28ee2626395f8e3a454da4dd02d4ea`
- Focused recovery/bookkeeping tests: **28 passed**
- Full backend suite: **1,354 passed, 3 skipped, 1 warning**
- Frontend production build: passed (`1,694` modules transformed)
- Isolated cumulative catalog: 120 artifacts, batches 01–12
- Catalog availability: 47 available / 67 conditional / 6 unavailable
- Catalog publication: 114 review-required / 6 withheld
- Catalog artifact-tree SHA-256:
  `520530a6de82328d12548e022db3282ccee367fa238999723770db1fa37421ef`
- Real localhost FastAPI list: HTTP 200, exact count 120
- Detail parity: 120/120; exact Batch 12 recovery parity: 10/10
- Calculator GET parity: 120/120
- Calculator POST parity: 114 numeric HTTP 200; six Withheld HTTP 400
- Private leaks: 0
- API receipt SHA-256:
  `f788d2bb9988d41d2c0f60c80481c44bb368bd30475845cc4a466587e095441e`

The API used an isolated untracked catalog and local auth harness with `save=false`. It verifies
real list/detail/calculator behavior, not real authentication, database/object-storage persistence,
or production serving promotion. Tracked serving roots match their pre-recovery hashes.

## Confirmation gate

The user confirmed the final Batch 12 recovery result on 2026-08-28. The whole-batch recovery
attempt is consumed. Do not recover Batch 12 again, start Batch 13, promote or activate a tracked
catalog, merge, push, or deploy without a separate explicit signal.
