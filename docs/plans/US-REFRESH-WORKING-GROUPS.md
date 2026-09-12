# U.S. valuation verified working groups

Checked 2026-09-11: 440 companies, 419 recipes, 263 compiled contracts, 156
implementation gaps, 1 current-version source-bound result and 0 explicit
successive-period results. Counts are work states, not one completion percentage;
prior source-bound results are not added across changed policy hashes.

Completed and user-confirmed: [WG0/WG1](archive/US-REFRESH-WG0-WG1-2026-09-09.md),
[WG2](archive/US-REFRESH-WG2-2026-09-09.md),
[WG3](archive/US-REFRESH-WG3-2026-09-09.md),
[WG4](archive/US-REFRESH-WG4-2026-09-09.md),
[WG5](archive/US-REFRESH-WG5-2026-09-09.md),
[WG6](archive/US-REFRESH-WG6-2026-09-09.md),
[WG7](archive/US-REFRESH-WG7-2026-09-09.md),
[WG8](archive/US-REFRESH-WG8-2026-09-09.md),
[WG9](archive/US-REFRESH-WG9-2026-09-09.md), and
[WG10](archive/US-REFRESH-WG10-2026-09-09.md), and
[WG11](archive/US-REFRESH-WG11-2026-09-10.md), and
[WG12](archive/US-REFRESH-WG12-2026-09-10.md), and
[WG13](archive/US-REFRESH-WG13-2026-09-11.md).

## Phase WG14 — ordinary and redeemable NCI carrying claims

Verified 2026-09-11; user confirmation pending. APD and CMI were retained under
the shared current NCI carrying mechanism. APD is source-bound; CMI is an
explicit source/economic review.

- APD now proves that $16.5964B total equity less $2.7126B total NCI equals
  $13.8838B parent equity. Its $1.8316B consolidated-VIE NCI is a subset, not an
  additional claim. Parent/common earnings drive residual income, so NCI is not
  deducted again; NCI investment, distribution and purchase flows remain
  diagnostics.
- CMI now binds $1.059B ordinary NCI separately from a $257M recognized guarantee
  carrying value, a $50M guarantee maximum, a $350M unconsolidated Amplify
  investment, $412M already contributed and $418M of future contributions. The
  two guarantee rows have unreconciled scopes and the future contribution lacks
  a timed schedule, so no candidate was issued.
- BAX was excluded because negative $27M NCI must stay diagnostic while $105M of
  separation/contingent claims remains separate. BLDR and DOV are no-NCI
  negative controls with unrelated bridge gaps, not carrying-claim cases.

APD and CMI passed the frozen two-worker evidence gate with their distinct
outcomes. APD also passed isolated real FastAPI/database activation, reload,
stale-CAS rejection and rollback. See
[WG14 evidence](../audit/wg14-ordinary-redeemable-nci.md).

## Next phase — NCI mixed with contingent and legal claims (queued)

Start with ABT and BAX. Inspect BA only if its NCI can be separated without
pulling the mandatory-convertible mechanism into the same rule. Keep current
NCI, negative NCI, acquisition liabilities, legal accruals, disposal-group
claims and historical owner flows separate. Do not start family adapters.

## Final release gate

All 440 accounted for; 419 update contracts or individually documented repairs;
successive real filings across required families; complete frozen comparison;
current UI/API/database and operational UAT; user approval. No production,
scheduling, merge, push or deployment before that gate.
