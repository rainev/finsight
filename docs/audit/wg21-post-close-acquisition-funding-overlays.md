# WG21 post-close acquisition funding overlays

Verified 2026-09-14 and user-confirmed 2026-09-15. This is a bounded working-group
result, not release approval. WG21 did not activate production, schedule work,
merge, push, deploy, start family adapters or process companies outside Batches
01–44.

## Retained mechanism and outcome

ECL and PH both have a completed acquisition after the controlling balance
date, but only ECL proves a complete bounded-overlay mechanism. ECL's June cash
and debt already include its pre-close acquisition financing; the August-filed
10-Q records the July close, price, operating scope, terminated undrawn bridge
facility and unavailable purchase accounting. The rule converts acquisition
cash into a 75% / 100% / 125% cost-based operating-asset proxy while applying a
105% / 100% / 95% cash-consideration sensitivity. The price remains an event
proxy, never intrinsic value or invented acquired FCFF.

PH's closing 8-K proves the $9.25B price and $5.25B + $2.50B loan draws, but says
the loans paid only a portion of price and related fees. The $1.5B difference is
therefore an unreconciled arithmetic funding gap, not a reported liability.
Without a post-close cash/debt/share/operating rollforward, PH remains financial
and source review. It was not marked unavailable and no candidate was issued.

## Company results

Ranges are exact low / base / high. Candidate changes compare with the frozen
historical recipes. Official serving changes remain zero because nothing was
activated.

| Company | Previous range | WG21 candidate/result | Exact candidate change |
|---|---:|---:|---:|
| ECL | 33.750181163523685 / 78.52498381981147 / 132.01884520511823 | 34.06202191416534 / 78.07933916802813 / 129.30056823405633 | +0.3118407506416574 / -0.4456446517833399 / -2.718276971061897 |
| PH | 168.4077188615264 / 344.41280130660505 / 566.2997603380239 | Source/economic review; no candidate | Not applicable; official change zero |

ECL's economic classification preserves current $5.1353B cash and $13.1708B
debt at base, separates $28.9M NCI, proves preferred equity zero, and deducts the
$334.4M net benefit deficit once ($533.8M liability less $199.4M plan asset).
The candidate movement comes from the current source share denominator and the
independently evaluated bear/bull overlay, not from treating $4.75B as intrinsic
value. The exact percentage changes are +0.9239676348128368%,
-0.5675195716129596% and -2.059006778038771%.

## Source classification

### ECL — source-bound representative

- Controlling 10-Q: accession `0001628280-26-053886`, period `2026-06-30`,
  filed `2026-08-06`; raw HTML SHA-256
  `e7f4323d48165a47f7c7ab2b70ae495d9399c43a1315be65c0917e91bdc39266`;
  structural SHA-256
  `d635d986157b4c7e78e73ef0e6d4e6b8424cdd2c1a96480d99821b86d17fe623`;
  package-manifest SHA-256
  `3bfac30edc89cc57f9831c18a26f61c7f0d4713178983691af6f92dff37dae5c`.
- Narrative receipt SHA-256
  `36682685d611e7a50fdde981e9bed986bedfe8d4f256559ece7d1e28338a2ca0`
  binds the exact document, sections, normalized-text locators, values, units,
  filing dates and extraction version. Its runtime file SHA-256 is
  `e5552c2a15db3848474df882bec45dc8cfb1541ab248be7f0ecc0b74bace005a`.
- The acquisition section reports the $4.75B agreement price subject to
  adjustment, July 2 close, Global Water operating scope, unavailable
  preliminary purchase allocation, immaterial/unpresented pro forma data, and
  expensed transaction/integration costs.
- The financing section reports $5B of notes used for CoolIT and general
  corporate purposes. The dedicated delayed-draw facility was terminated
  undrawn. The current debt aggregate reconciles exactly to $1.2657B current +
  $11.9051B noncurrent; no bridge financing is added again.
- $32.8M benefit contributions and $18.9M benefit expense are operating/cash-
  flow diagnostics, not additional bridge claims. Current NCI and the benefit
  deficit remain separate.

### PH — difficult fail-closed case

- Controlling 10-Q: accession `0000076334-26-000073`, period `2026-03-31`,
  filed `2026-05-01`; raw HTML SHA-256
  `edb2f35a83ebfcec4804f906e2f626444d866b777b653643843f879decbbe416`;
  structural SHA-256
  `e2acbe75d6696949ce48fe652d10bfdd6bc9100196de2f35d41dd19592e5bcc7`.
- Completed-acquisition 8-K: accession `0001193125-26-349148`, filed and dated
  `2026-08-13`; document SHA-256
  `f6016eedbb5db59e69f3b056f8d5b7173187aa19b984200993dd30851f477f61`.
- The clean narrative manifest carries only filing identity and document hash;
  it intentionally drops the legacy receipt's derived residual-funding field.
  Manifest file SHA-256:
  `ea8dd03cf9bf14aa67125508025e57d06ad6377cd0d2c1e82f09a40b54b3eb78`.
  Narrative receipt SHA-256:
  `9f087316bfde46c654c4af1b7231a6d0da1063ac20cea6fe5115782025e1d3da`;
  runtime file SHA-256
  `50b67c2b4765aa1ccab3b3cb7579548dd0ac83b99494c7e62e73ba8a629d1492`.
- The current structural debt components are $2.1B commercial paper, $2.813B
  current debt and $6.769B noncurrent debt, or $11.682B before the event. This
  exposes the legacy recipe's omitted current-debt component; it is not repaired
  mechanically while the post-close funding state remains unresolved.
- Current NCI is $8M. Preferred carrying value and issued shares are zero. The
  event loans total $7.75B, but neither the remaining funding source nor the
  post-close cash, debt, shares, purchase accounting and acquired cash flow are
  reported in the retained evidence.

## Verification evidence

- Frozen source index:
  `output/us-refresh-runtime/source-indexes/adfd8fc22f6f2d06dea1484280fff26863b1f5eeadc82028f4d0f1fe02374a2d.json`,
  file SHA-256 `0d38ec5d8b427528d8412809db98d6f0ec994c8a2c1c388d7a236acfa45356a8`.
- Direct cached-source report:
  `output/us-refresh-runtime/source-validation/c0659323dcd89ef8622dc9e8321fa1ce422ab1724b34a853cdf4162e5054da97/report.json`,
  SHA-256 `c0659323dcd89ef8622dc9e8321fa1ce422ab1724b34a853cdf4162e5054da97`.
  Outcome: ECL source-bound and PH source/economic review on implementation
  SHA-256 `83874002c67d9ada50ff5125d0e45d7a4804bb90970fb66ca7d850297b8dab5b`
  and policy SHA-256
  `baf9547ce61d99bf319f5d8897f2404438ad33b51e7715eaa7e06fb4ed9fa0fa`.
- Frozen two-worker group:
  `output/us-refresh-group-verification/8fe663e6695181bbb8bf8301ea6c824734142e74e2df19b935a37190ef0b33b8/report.json`,
  file SHA-256 `5432851f123c90f7a6c8bbef4c14402458834e7cc128ee1b0068ccbe61225499`.
  One worker handled ECL and one PH; both reproduced the direct result.
- Focused cross-module regression: **585 passed**, one existing Passlib `crypt`
  deprecation warning, in 167.45 seconds. It covers every refresh module,
  calculation recipes, the two relevant batch engines, source ingestion,
  narrative receipts, real cached event exhibits, group verification,
  calculators and catalog behavior.
- ECL passed isolated real FastAPI/database activation, worker reload, stale-CAS
  rejection and rollback:
  `output/us-refresh-operational-uat-20260914-wg21-ecl-final/uat-report.json`,
  SHA-256 `30ae466ecb11772d5843af943fcad8b95a9b9c24f1f85362f60b9a68c96178b0`.
  It retained 440 registry entries and 419 recipes and reports
  `production_runtime_touched=false`.
- PH's isolated localhost API served exact frozen detail and calculator parity
  with no candidate activation:
  `output/us-refresh-runtime/wg21-ph-blocked-api-evidence.json`, SHA-256
  `4275ef761d6819288f1108aeb418cc2b9b15fe1282a0b149baa3fdd4c276fb38`.
- Current work register: 440 companies, 419 recipes, 279 compiled contracts,
  140 implementation gaps, 194 financial reviews, 166 source gaps, one current-
  policy source-bound result and zero successive-period proofs. Readiness remains
  honestly incomplete at 279/419.
- No frontend behavior changed, so the redesigned browser was not mechanically
  rerun. `git diff --check` is required before presenting the gate.

Two Luna xhigh reviewers independently audited ECL and PH. The primary agent
rechecked their source locators and economic conclusions, implemented the shared
rule, and exercised the real cached-source, two-worker and API/database paths.

## Remaining blockers

- PH needs a source-bound residual funding classification and a post-close
  cash/debt/share/operating rollforward. The old $1.5B preferred-slot assumption
  is not accepted as evidence.
- ECL still lacks final purchase accounting and comparable acquired cash-flow
  history. Its result is a Low-reliability bounded event proxy, not a normal
  intrinsic acquired-business valuation.
- Neither company has successive-period proof. Cached verification does not
  establish live future event-exhibit coverage.
- The complete pipeline remains unfinished with 140 implementation gaps and
  zero successive-period proofs elsewhere in the 440-company register.
