# WG13 minority-interest ownership claims

Verified 2026-09-10; user confirmation pending. This is a bounded working-group
result, not release approval. Production, scheduling, merge, push, deployment,
later batches and family adapters were untouched.

## Retained mechanism

AOS and Agilent were retained as the two forms of source-proven no issuer NCI.
AOS is the clean absence case. Agilent is the difficult exclusion case: an
NCI-named XBRL fact belongs to an unconsolidated not-primary-beneficiary VIE
investment disclosure, not the consolidated owner-claim bridge.

The new Agilent rule requires the complete filing package, current accession and
period, `VariableInterestEntityNotPrimaryBeneficiaryDisclosuresAbstract`
ancestry, no balance-sheet role, a matching reported long-term-investment total,
and no conflicting current consolidated NCI fact. It returns issuer NCI zero but
retains the $44M VIE exposure privately. It also removes generic
`LongTermInvestments` from cash-like securities so the same exposure cannot be
added separately. The rule contains no filing amount or date.

AOS uses the existing complete-balance-sheet zero-NCI contract. Current assets
of $3.6445B equal liabilities of $1.8026B plus parent equity of $1.8419B, with no
ordinary, redeemable, temporary, preferred or VIE claim. Current debt is the
disjoint $39.5M current plus $598M noncurrent amount; no missing lease or
commercial-paper balance is invented.

## Five-company result

| Company | Classification | Previous low / base / high | Current low / base / high |
|---|---|---|---|
| AOS | Retained representative; source-proven zero issuer NCI | 30.082417499499776 / 53.90931573480934 / 83.83956195239817 | 29.80578470819966 / 52.93286269583466 / 81.55491396994866 |
| A | Retained difficult exclusion; $44M unconsolidated VIE investment exposure, not issuer NCI | 33.36726191087803 / 65.7289157327362 / 103.86497668215685 | No candidate; unrelated bridge review preserved |
| ABT | $652M ordinary NCI plus $263M acquisition consideration and $510M legal/environmental accrual | 29.689388909506913 / 58.20809920073297 / 89.65169838253692 | No candidate; mixed-claim implementation gap preserved |
| BA | $15M ordinary NCI plus mandatory-convertible preferred and separate legal exposure | 0 / 4.039475664565482 / 60.95483472313898 | No candidate; implementation gap preserved |
| CAT | Negative $1M NCI diagnostic in parent-equity captive-finance model | 59.983247289782966 / 159.69657342768494 / 334.6347927700216 | No candidate; current filing-selection review preserved |

AOS changes are -0.2766327913001163 / -0.9764530389746824 /
-2.2846479824495134 per share (-0.9195829800072275% /
-1.811288133906297% / -2.725023758767575%). Its ownership bridge remains
zero. The movement comes from current source cash conversion and the locked
138,511,483-share denominator rather than any invented NCI adjustment.

Agilent's earlier $44M deduction is no longer accepted as an ownership claim,
but no replacement range is issued because commercial paper, finance leases and
current marketable securities remain unresolved. ABT's $11M/$12M custom NCI
roll-forward is net of income, distributions and repurchases and is not used as
a balance or pure NCI earnings. BA's $172M preferred dividends, $5.75B
liquidation preference and 33.511M–40.216M future conversion shares stay
separate from $15M NCI and the $1.115B legal possible-loss surface. CAT's
negative NCI is not inverted into common value; its model already uses parent
equity and requires no second NCI deduction.

## Verification evidence

- Agilent controlling filing: accession `0001090872-26-000055`, period
  `2026-04-30`; structural SHA-256
  `7ea2dfdce833de652b223127f8fecfc3f731eb9805e71d18890c818d750d598a`;
  raw filing SHA-256
  `4fdc1e2c6130156c099140df4258ce7fa04d7c4cd737ae0574e733a9f512f80f`.
- AOS controlling filing: accession `0000091142-26-000098`, period
  `2026-06-30`; structural SHA-256
  `81eb6237c21c5543aeb25d70647c5c4cb4864727c455fb32f3a868d455a40dc6`;
  raw filing SHA-256
  `fc40bdae8bb18aebecba86434fad976db9e4f5fe4fdba49331bdc3869223797e`.
- Five-company direct source report:
  `output/us-refresh-runtime/source-validation/4f2c9b51b4ea65b88fec450627819ff5796c88156eaa59654c2ea73b8320b0ba/report.json`,
  SHA-256 `4f2c9b51b4ea65b88fec450627819ff5796c88156eaa59654c2ea73b8320b0ba`.
- Frozen two-worker retained group:
  `output/us-refresh-group-verification/d173a94e26759a240379746a5fdea1ae9e80b31f391cde8b27f8bd5641cc6173/report.json`,
  SHA-256 `b2205bdcf9b81cf0fc3e97ee9117d0e73da4132746109ff957d22836eb8efec1`.
  Outcome: one source-bound candidate and one exact source/economic review.
- Focused regression: 149 passed; one unrelated dependency deprecation warning.
- Isolated AOS API/database UAT:
  `output/us-refresh-operational-uat-20260910T052532Z-35a0b3ec/uat-report.json`,
  SHA-256 `79c804630860102506974acd99a2df5bd834aa73d04177193bc4fd3e934267b7`.
  A real FastAPI worker served predecessor/candidate/rollback values, reloaded
  without restart, rejected stale CAS and preserved 440 companies plus 419
  private recipes. Production was not touched.
- Work register: `output/us-refresh-work-register.json`, SHA-256
  `3736afa9a29a8c2473d5c1d33696ff05cf3dc7efaa9522bd8dc997ab8d51fd14`.
  Counts: 262 compiled contracts, 157 implementation gaps, one current-policy
  source-bound result and zero explicit successive-period proofs.

Two Luna xhigh reviewers independently inspected A/ABT and AOS/BA. The primary
agent separately inspected CAT, corrected the Agilent interpretation after the
independent challenge, integrated the final A/AOS rules, and reran the source
calculations and runtime evidence.

## Remaining blockers

- Agilent needs current commercial-paper, finance-lease and marketable-security
  coverage plus its cutoff-safe post-period financing bridge before a new value
  can be issued.
- ABT needs $652M ordinary NCI separated from its $263M acquisition carrying
  liability and $510M legal/environmental accrual; its net roll-forward flow
  cannot substitute for parent-attributable earnings.
- BA needs a dedicated legal/preferred/NCI rule; neither its $5.75B liquidation
  preference nor future conversion shares may be mixed with ordinary NCI.
- CAT's current residual-income filing selection is incomplete. Its negative
  NCI remains diagnostic and must never become a common-equity asset.
- No company has successive-period proof under the current release candidate.
