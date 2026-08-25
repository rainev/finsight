# Batch 02 conditional-estimate policy gap audit

**Valuation date:** 2026-08-14

**User decision:** publish a practical value even when major future-event assumptions are not
source-proven, provided the number is plainly labeled, reliability is Low, and the warning explains
why the estimate may be wrong.

## Product boundary

The existing strict and practical intrinsic-value decisions remain valid comparison evidence. This
phase adds a separate `conditional_estimate` surface; it does not relabel estimates as reported
facts, silently clear the universe-reset withheld register, or alter serving data before approval.

## Gap register

| ID | Severity | Gap | Smallest implementation |
| --- | --- | --- | --- |
| CE-01 | P0 | Public model vocabulary has no honest identity for a conditional/event estimate | Add allowlisted `conditional_estimate`; retain `review_required` and Low reliability |
| CE-02 | P0 | Six private outcomes do not calculate hypothetical states | Add frozen issuer-specific formulas with reported facts and separately tagged governed assumptions |
| CE-03 | P0 | Public artifacts cannot explain the number briefly | Add one short review warning; keep full assumptions and source trace private |
| CE-04 | P0 | CHTR conservative/base residual equity is negative | Publish an `equity_at_risk` conditional range with a $0 downside floor and explicitly conditional upside; never turn a negative residual into a fabricated ordinary base |
| CE-05 | P0 | WBD merger consideration can be mistaken for intrinsic value | Keep standalone normalization and contractual $31 plus ticking consideration as separately identified event states; never probability-weight |
| CE-06 | P0 | Commitments or transaction claims can be counted twice | Record bridge arithmetic privately and add monotonic/double-count tests |
| CE-07 | P0 | Conditional output could leak private evidence or mutate serving files | Reuse sanitizer, stage only under `output/`, verify real API, preserve protected hashes |
| CE-08 | P1 | Existing register records source-bounded withholding | Leave it unchanged until user approval; report conditional numeric completion separately |

## Issuer method decisions

| Ticker | Conditional method | Load-bearing uncertainty |
| --- | --- | --- |
| OMC | Annualized post-combination operating run-rate less bridge claims | Combined history and normalization multiple |
| TTWO | Release-outcome revenue × cash margin × equity multiple | GTA VI timing/reception/profitability |
| CHTR | Current-state and announced-transaction residual equity paths | Cox/Liberty claims, dilution, and unfiled combined cash flow |
| CMCSA | Current consolidated five-year FCFF DCF | Future separation debt/cash/corporate-cost allocation |
| META | Revenue × cash-conversion margin × equity multiple | AI capex returns and commitment/lease overlap |
| WBD | Normalized standalone FCFF states plus separate contractual merger consideration | Standalone normalization and conditional close |

## Gate

Implementation must prove exact arithmetic, ordered finite/nonnegative conditional ranges, Low
reliability, honest model/output labels, correct sensitivity direction, zero missing-as-zero
substitution, zero private leaks, deterministic A/B equality, complete backend regression, real API
list/detail parity, and unchanged serving roots. Stop after presenting the six values for user
confirmation; do not remove register entries, start Batch 03, merge, deploy, or promote.

