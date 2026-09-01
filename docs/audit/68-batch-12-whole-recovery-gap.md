# Batch 12 Whole-Recovery Gap Audit

Status: **audit complete; recovery implementation authorized by the user**. This audit compares
the verified initial Batch 12 candidate-i with the user's request for a more useful whole-batch
recovery because several values appear economically off. It does not use market prices, analyst
targets, or post-cutoff filings.

## Reference

The governing reference is the baseline-decision policy in
`docs/audit/37-finsight-baseline-decision-policy.md`: use reported TTM and longer history, choose an
economically suitable model, use transparent industry/company-normalized growth and risk, and
withhold only for a hard failure. The user's recovery signal applies that policy once to all ten
Batch 12 issuers, including current Conditional results.

The approved initial comparison surface is
`output/batch-12-history/candidate-i/batch-12-report.json` and Audit 67. It remains immutable
evidence; recovery must produce separate outputs.

## Ours today

- ✔ Candidate-i is mechanically coherent: exact source identities, periods, units, share
  denominators, current bridges, TTM arithmetic, ordered sensitivities, and public/private parity
  all pass.
- ✔ The initial result is 0 Pass / 9 Conditional / 1 Withheld, with bases from $6.87 for BAX to
  $149.70 for LLY.
- ✔ Seven operating issuers use the same five-year constant-growth cash-FCFF function. Every one
  uses terminal growth `(0%, 1%, 2%)`; growth is hard-capped to at most 3%/4%/5% in
  `batch_12_history.py` even when issuer history is materially different.
- ✔ HUM and CVS use source-linked parent/common earnings, but turn them into value with fixed
  5x/8x/11x and 4x/7x/10x multiples. Book equity, ROE and dividends are not used to establish the
  valuation level.
- ✔ UHS is fully withheld because the completed July Ireland acquisition moved the balance sheet
  after June 30 while Talkspace remained pending.

## Reuse check

The project already has the required recovery components:

- `EnterpriseCashFlowState` and `enterprise_cash_flow_dcf` implement an eight-year cash-FCFF
  forecast with explicit growth fade and a terminal-growth ceiling of 2.5%.
- `residual_income_valuation` values common equity from book value, ROE, payout, required return,
  and terminal economics without treating insurer operating liabilities as ordinary debt.
- Batch 11 recovery preserves initial artifacts, records one attempt, stages public-safe output,
  and protects serving roots.
- The cumulative watchlist/register loaders and catalog builder already enforce exact identities,
  counts, and public-safety boundaries.

Recovery should compose these components rather than introduce a parallel general valuation
engine.

## Flow

Current flow:

`cutoff-safe filing -> current TTM/history -> blanket five-year DCF or fixed earnings multiple -> candidate-i range`

Required recovery flow:

`same frozen evidence -> issuer/event-aware scale -> source-normalized cash or common-equity state -> faded DCF/residual income -> independent cross-check -> recovery artifact -> watchlist/register -> real API`

The source layer is not the failing surface. The gap is between correctly extracted inputs and the
model/calibration that turns them into a useful baseline.

## What backs the recovery

- ✔ ABT's controlling filing reports pro-forma combined H1 2026 revenue of $24.5B and pretax
  earnings of $2.9B, compared with only $1.0B of Exact Sciences sales inside reported H1. The
  initial bridge already carries the full acquisition debt and acquisition claims. The same filing
  reports a separate $510M recorded legal/environmental accrual that candidate-i omits.
- ✔ LLY reports H1 revenue of $42.773B versus $28.286B in the comparative H1. Its source-linked
  annual-growth history has a 25.78% median, while candidate-i uses 4% base growth.
- ✔ HUM reports $19.213B parent equity and $214M H1 dividends; CVS reports $79.702B parent equity
  and $1.725B H1 dividends. Both have source-linked five-year common-earnings histories.
- ✔ UHS reports a completed approximately $188M Ireland purchase, $1.272B available revolver
  capacity at June 30, and an $835M Talkspace transaction explicitly expected to use additional
  borrowings. It also reports July Provo Canyon license revocations/patient discharges and an
  August CMG operating-responsibility transition. A $188M reserve alone does not reconstruct that
  post-period operating and financing state.
- ✔ BAX reports a $43M net separation indemnification liability and a separate $52M remaining
  contingent capital-expenditure reimbursement liability. Candidate-i subtracts only $10M of
  other contingent consideration.
- ✔ BDX completed its spin and received a $3.857B net distribution already visible in the cash-flow
  statement; it must not be added again. BMY's $607M CVR, RVTY's $8M contingent claim, and the
  issuer-bound supplier-finance treatments are already correct.
- ✔ BDX reports a $1.6B product-liability/legal accrual payable over multiple years. BMY closed its
  Hengrui arrangement in July with $600M upfront and two $175M anniversary payments, plus
  contingent milestones up to $14.3B. LLY paid approximately $2.0B in July for three companies
  with up to $3.9B consideration and has a separate pending approximately $2.8B AtaiBeckley deal.

## Gaps

- **B12R-01 · P0 ✔ — One blanket operating model suppresses issuer economics.** Seven companies
  use a constant-growth five-year DCF despite the existing faded cash-FCFF engine. The arithmetic
  is correct, but the model does not distinguish post-acquisition scale, mature patent runoff,
  high-growth pharma, or post-divestiture cash. Recovery must use coupled issuer-specific cash and
  growth states with an eight-year fade and terminal growth capped at 2.5%.
- **B12R-02 · P0 ✔ — ABT mixes a partial Exact Sciences operating stream with the full post-deal
  bridge and omits a recorded legal claim.** Candidate-i uses $46.585B reported TTM revenue while
  deducting the post-close debt and acquisition claims. The filing supplies $24.5B H1 pro-forma
  combined revenue and a $510M legal/environmental accrual. Recovery may use annualized $49.0B
  combined scale only with historical cash margins and explicit pro-forma limitations; it must
  bind and subtract the recorded accrual once.
- **B12R-03 · P0 ✔ — LLY's growth is severed from its current/history evidence.** The generic cap
  converts a 25.78% historical median and 51.2% current H1 growth into a 4% base. Recovery must
  use a conservative high-growth state below the reported history/current rate and fade it to a
  2.5%-or-lower terminal rate; it must also include a genuine pipeline/patent downside state.
- **B12R-04 · P1 ✔ — HUM/CVS fixed multiples lack a source-level valuation anchor.** The equity
  route is correct, but the multiple level is a pure policy constant. Recovery should use residual
  income on reported common equity, source-linked normalized earnings/ROE, and reported payout,
  retaining the multiple result only as a diagnostic.
- **B12R-05 · P0 ✔ — UHS's source-complete recovery remains Withheld.** The exact Ireland funding
  split is absent, and the filing also records post-period license revocations, patient discharges,
  and a new physician-group operating responsibility. A $188M financing reserve is a useful
  diagnostic but does not create one post-Ireland operating/cash/debt object. The authorized
  attempt must retain UHS as Withheld and record these additional blockers.
- **B12R-06 · P1 ✔ — BAX omits $95M of retained separation claims.** The $43M indemnification and
  $52M contingent capex reimbursement liabilities are current issuer obligations distinct from
  the $10M contingent-consideration claim. Recovery must bind and subtract all three once. The
  indemnified $28M legacy guarantees remain disclosure-only because Carlyle reimburses them.
- **B12R-07 · P0 ✔ — BDX, BMY, and LLY omit material recorded or post-period claims/events.** BDX
  must bind and subtract its $1.6B recorded product-liability/legal accrual. BMY must bind the
  $600M plus two $175M fixed Hengrui payments without probability-weighting the $14.3B maximum.
  LLY must reserve the approximately $2.0B already paid for July acquisitions, bind the $3.9B
  maximum/three-company event, and keep pending $2.8B AtaiBeckley outside intrinsic value.
- **B12R-08 · P1 ✔ — WST has sale cash but no comparable post-sale operating history.** Adding the
  $136M proceeds is correct, but pre-sale cash history still includes SmartDose. Recovery may
  revalue through the faded cash model only as Conditional and must not claim a fully continuing
  history or invent a disposed-business cash adjustment.
- **B12R-09 · P1 ✔ — Whole-batch recovery orchestration is missing.** There is no Batch 12 recovery
  module, immutable runner, exact attempt receipt, recovery test suite, or post-attempt bookkeeping
  path. These must be added without modifying initial evidence or serving roots.
- **B12R-10 · P2 ✔ — Structural flow rows can show `filed: null`.** The inherited helper reads
  `filed` instead of top-level `filed_date`. Controlling receipts/accessions still prove cutoff, so
  this is provenance display work and does not block recovery.

## Reconciled lens disagreement

The source/arithmetic lens found no remaining Critical/Important defect in candidate-i. The
economic-usefulness lens nevertheless found B12R-01 through B12R-06. These are not contradictory
claims: candidate-i faithfully computes the policy it was given, while the policy is too generic
for the user's useful-baseline reference. Recovery therefore changes model calibration and
economic-object handling without rewriting source facts or price-fitting the answer.

## Gate

Audit gate passed. Roll B12R-01 through B12R-09 into one authorized Batch 12 recovery phase. Do
not start Batch 13, fetch new sources, use market prices, promote serving artifacts, push, or deploy.
