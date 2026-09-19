# U.S. valuation verified working groups

Checked 2026-09-12: 440 companies, 419 recipes, 269 compiled contracts, 150
implementation gaps, 0 current-version source-bound results in the latest
three-company report and 0 explicit
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
[WG13](archive/US-REFRESH-WG13-2026-09-11.md), and
[WG14](../audit/wg14-ordinary-redeemable-nci.md), and
[WG15](../audit/wg15-nci-mixed-contingent-legal-claims.md), and
[WG16](../audit/wg16-nci-acquisition-litigation-overlaps.md).

## Phase WG14 — ordinary and redeemable NCI carrying claims

Verified 2026-09-11 and user-confirmed 2026-09-12. APD and CMI were retained under
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

## Phase WG15 — NCI mixed with contingent and legal claims

Verified and user-confirmed 2026-09-12. ABT is a current-version
source-bound candidate. BAX has a compiled claim contract but remains blocked
on cash/securities bridge evidence. BA's ordinary NCI is separately evidenced,
but its mandatory-convertible preferred and legal/guarantee surfaces remain an
implementation gap and were not folded into WG15.

- ABT binds $652M ordinary NCI, $263M contingent consideration and a $510M
  legal/environmental carrying accrual separately. Aggregate/Level-3 duplicate
  presentations, possible-loss ranges, environmental maxima and damages flows
  remain non-additive. Its filed Exact Sciences pro-forma revenue supplies the
  operating scale; historical cash margins and current shares remain separate.
- BAX binds a $105M stack of current acquisition, separation-indemnification
  and disposal-group claims. Its negative $27M NCI remains a diagnostic and is
  not inverted into common value. The $133M maximum, $28M retained guarantees,
  $39M legal reserve with $25M environmental subset, and $31M paid cash remain
  separate.
- BA binds only its $15M ordinary NCI as evidence. The live mandatory-convertible
  preferred, $971M environmental accrual, $1.115B possible-loss amount, guarantee
  and repurchase scopes require a later dedicated mechanism.

The three-company frozen two-worker group and ABT isolated FastAPI/database
activation, reload, stale-CAS rejection and rollback passed. See
[WG15 evidence](../audit/wg15-nci-mixed-contingent-legal-claims.md).

## Phase WG16 — remaining NCI/acquisition/litigation overlaps

Verified and user-confirmed 2026-09-12. DGX is source-bound. BSX and EW
prove the shared claim components but remain blocked by separate economic
conditions.

- DGX binds $303M ordinary NCI, $80M redeemable NCI and $100M current
  contingent consideration. Its $174M malpractice and $17M litigation reserves
  remain operating liabilities rather than a second equity-bridge deduction.
- BSX binds $242M NCI, $257M contingent consideration and $282M legal accrual,
  but its $600M–$700M post-period restructuring cash lacks a timed schedule.
- EW binds $106.9M NCI, a $9.9M aggregate contingent carrying value with $7.5M
  current portion, and a $56.9M legal reserve without adding the $72.4M combined
  litigation/insurance balance. Unaccrued patent, milestone, appeal and tax
  exposure remains unbounded.

The frozen two-worker flow reproduced one source-bound candidate, one
implementation gap and one source/economic review. DGX passed isolated real
FastAPI/database activation, reload, stale-CAS rejection and rollback. See
[WG16 evidence](../audit/wg16-nci-acquisition-litigation-overlaps.md).

## Phase WG17 — ordinary/redeemable NCI with contingent consideration

Verified and user-confirmed 2026-09-12. DVA and CRL prove the shared
current ordinary/redeemable-NCI mechanism but remain explicit source/economic
reviews. ZBH does not report redeemable NCI and was excluded.

- DVA binds $283.118M ordinary NCI and $1.561416B redeemable NCI. Its $39.463M
  acquisition obligation is already inside $10.781013B aggregate debt, and a
  later $200M Elara investment lacks a post-event rollforward.
- CRL binds $6.354M ordinary NCI, $42.537M redeemable NCI and $45M current/
  noncurrent contingent consideration. A separate $105M deferred-consideration
  liability has unresolved cash-flow overlap; securities and derivative claims
  remain unbounded.
- ZBH reports $8.7M ordinary NCI but no redeemable-NCI carrying balance. Its
  acquisition, litigation, China-distributor and tax surfaces belong to a
  different rule.

The frozen two-worker flow reproduced two source/economic reviews and one
implementation gap. The isolated real API served exact prior detail/calculator
parity for all three and proved that no candidate catalog was activated. See
[WG17 evidence](../audit/wg17-nci-redeemable-contingent-claims.md).

## Phase WG18 — ordinary NCI with acquisition carrying claims

Verified 2026-09-12 and user-confirmed 2026-09-13. GLW, MDT and PFE each bind a
current ordinary-NCI balance and a separate acquisition carrying liability.
The frozen two-worker run produced three source-bound candidates. GLW and PFE
preserve their claim totals after semantic reclassification; MDT removes a
second deduction of its operating legal reserve. All three passed isolated
FastAPI/database activation, reload, stale-CAS rejection and rollback, with
production untouched. See
[WG18 evidence](../audit/wg18-ordinary-nci-acquisition-claims.md).

## Phase WG19 — remaining mixed ordinary-NCI claim stacks

Verified 2026-09-13 and user-confirmed 2026-09-14. HSIC and ON produced
source-bound candidates after ordinary/redeemable NCI, acquisition carrying
claims and operating reserves were separated. ZBH's current facts reconcile but
its distributor/tax exposure remains unbounded, so it stays financial review.
TEL was excluded because it has redeemable NCI but no ordinary-NCI balance. The
two-worker flow and isolated API paths preserved production. See
[WG19 evidence](../audit/wg19-mixed-ordinary-nci-claim-stacks.md).

## Phase WG20 — remaining NCI/acquisition special situations

Verified and user-confirmed 2026-09-14. TEL and CRWD produced
source-bound candidates after redeemable/ordinary NCI, acquisition liabilities,
explicit legal/environmental reserves, paid cash, pending events and operating
purchase schedules were separated. PH was excluded because its economics depend
on a post-close transaction/funding overlay rather than a current carrying-
liability rule. The two-worker flow and isolated API paths preserved production.
See [WG20 evidence](../audit/wg20-nci-acquisition-special-situations.md).

## Closed

WG21 delivered one ECL bounded-overlay candidate and explicit PH funding review; user-confirmed 2026-09-15 — [archived phase evidence](archive/2026-09-15-us-refresh-wg21.md).

WG22 delivered one ETN candidate and retained HCA/HON blockers; user-confirmed 2026-09-15 — [archived phase evidence](archive/2026-09-15-us-refresh-wg22.md).

## Phase WG23 — ordinary-NCI carrying leftovers (closed)

Checked 2026-09-15 against current source tests, two-worker and isolated API
evidence. JBL/INTC current ordinary NCI reconciles; LHX/MCK are excluded for
distinct redeemable claims. JBL retains a new-lease full-carrying/overlap source
gap; INTC retains its explicit governed-margin migration gap. No numeric
successor was issued. Two Luna High reviews and the primary source recheck
support the exception gate; 595 broad tests and 25 post-review focused checks
passed. User-confirmed 2026-09-15. See
[WG23 evidence](../audit/wg23-ordinary-nci-carrying-leftovers.md).

## Phase WG24 — explicit governed cash-margin normalization (closed)

Use INTC following WG23 confirmation. Migrate its retained governed cash
margins separately from source cash/history, preserving capex, growth support,
negative annual observations and current ownership/debt. Add no more than two
companies only if existing approved rules genuinely share the mechanism. Do not
change approved parameters or begin family adapters. Current real-source narrow
replay preserves all values; complete refresh remains named economic/source
review. Final 609 checks, independent challenge, frozen two-worker repeat and
isolated six-company API parity passed. User-confirmed 2026-09-15. See
[WG24 evidence](../audit/wg24-governed-cash-margin-normalization.md).

## Phase WG25 — finance-lease and capital-payment overlap (confirmed partial gate)

INTC/JBL following WG24 confirmation, only genuinely shared source mechanisms.
Preserve current cash/AFS and transformation review and all prior claim-stack
blockers. No automatic extra-capex/debt deduction or inferred payment schedule.
Shared source ledger and hash-bound narrative scope are implemented; current
carrying/overlap remains required source/economic work. Both independent
challenges, frozen repeat, six-company isolated API parity and 626 current
regressions pass. Narrow-result user-confirmed, not completed
company refreshes. See [WG25 evidence](../audit/wg25-lease-capital-payment-overlap.md).

## Phase WG26 — remaining redeemable-ownership claim stack (confirmed partial gate)

LHX and MCK share only explicitly typed non-additive carrying aliases, not a
preferred/conversion economic rule. Real frozen partial proofs, exact legacy
reclassification, 640 regressions, independent guard review and isolated six-
company API parity pass. Narrow-result user-confirmed; neither full
implementation gap is cleared. WG26-S1/H1 remain required. See
[WG26 evidence](../audit/wg26-redeemable-ownership-stack.md).

## Phase WG27 — subsidiary preferred/derivative economic bridge scope (confirmed partial gate)

LHX source accounting/host/proceeds/program/derivatives reconcile; exclusive
economic-basis guards prevent cash/dilution double count. Stable 658 checks,
independent 18-check challenge, frozen repeat and isolated API parity pass.
Narrow-result user confirmed 2026-09-16, not complete preferred economic value.
WG27-S1 and environmental/MCK/lease/portability/HCA/HON/hardening remain required.
See [WG27 evidence](../audit/wg27-subsidiary-preferred-bridge.md).

WG28 narrow ledger/blocked-update gate user-confirmed 2026-09-16 —
[archive](archive/2026-09-16-us-refresh-wg28.md); full overlap remains required.

WG29 narrow annual-source/blocked-update gate user-confirmed 2026-09-16 —
[archive](archive/2026-09-16-us-refresh-wg29.md); full LHX gaps remain required.

WG30 narrow scoped-payment/conditional diagnostic gate user-confirmed 2026-09-16 —
[archive](archive/2026-09-16-us-refresh-wg30.md); full MCK gaps remain required.

WG31 narrow source/mechanism gate user-confirmed 2026-09-16 —
[archive](archive/2026-09-16-us-refresh-wg31.md); full MCK gaps remain required.

WG32 narrow official-source/floor/blocked-contract gate user-confirmed 2026-09-16 —
[archive](archive/2026-09-16-us-refresh-wg32.md); full MCK gaps remain required.

WG33 narrow governed ownership-carrying/value-neutral gate user-confirmed —
[archive](archive/2026-09-16-us-refresh-wg33.md); full MCK gaps remain required.

WG34 narrow ledger/nonadditivity/blocked-update result user-confirmed 2026-09-17 —
[archive](archive/2026-09-17-us-refresh-wg34.md); full HCA runoff remains required.

## Phase WG35 — HCA annual professional-liability cash evidence (USER-CONFIRMED)

Both authorized HCA annuals captured. Reconcile gross/current/noncurrent/net
reserves, recognized reinsurance, paid claims, provisions, restricted investments
and OCF without historical double count. Current multi-year runoff remains absent,
so preserve the bounded noncurrent sensitivity and every prior gap. Focused22,
independent, frozen, broad788 and API verification pass. No numeric successor
or completed HCA refresh. [WG35 audit](../audit/wg35-hca-annual-professional-liability-cash.md).

## Phase WG36 — HON separation scope (USER-CONFIRMED)

Implement and verify actual-close/split/event classification from cached HON
evidence. Preserve continuing-parent FCFF and event funding as unknown until
source reconciliation. HONA carve-out observations are corroborating audit
evidence, with no new HONA valuation. [WG36 audit](../audit/wg36-hon-separation-scope.md).

Narrow source/safety result verified:25 focused/14 independent/802 broad checks,
frozen repeat and isolated API. Narrow result user-confirmed. Full HON economic
reconciliation is still required; no later group or source acquisition started.

## Phase WG37 — HON closing agreements (USER-CONFIRMED)

Two authorized HON 8-Ks and selected direct separation/contract/pro-forma/
earnings exhibits captured. Bind exact dated surfaces; retain current bridge and
enterprise FCFF as unknown. [WG37 audit](../audit/wg37-hon-closing-agreements.md).

Narrow source/economic safety result verified: focused36, independent9,
broad811, frozen repeat and isolated API pass. Narrow result user-confirmed. No
numeric successor or current HON refresh.

## Phase WG38 — pharmaceutical contingent claims (USER-CONFIRMED)

Checked 2026-09-18 against current BIIB, GILD and INCY cached filings. A shared
role-based rule now distinguishes recognized carrying liabilities from duplicate
fair-value presentations, CVR/milestone ceilings, paid cash, legal disputes and
royalty obligations. BIIB remains legal-scope review; GILD and INCY bind their
claim/cash ledgers but remain blocked by broader current bridge fields. No
numeric successor, value change or release action. [WG38 audit](../audit/wg38-pharma-contingent-claims.md).

## Phase WG39 — pharmaceutical current bridge (USER-CONFIRMED)

Checked 2026-09-18 against current GILD and INCY cached filings. Source-bound
cash, securities, debt, NCI/preferred, royalty/claim overlap, structural TTM and
dated cash rules produce two Low candidates. Frozen workers, independent
challenge, broad regression and real isolated API/calculator activation/reload/
rollback pass; production remains unchanged. [WG39 audit](../audit/wg39-pharma-current-bridge.md).

## Phase WG40 — BIIB legal and post-Apellis scope (NOW)

Checked 2026-09-19 against cached BIIB current/annual filings. Acquisition claim
and current bridge reconcile, but legal carrying/payment/recovery, comparable
acquired cash, exclusive integration payments and pending-event cutoff scope do
not. No successor; GILD/INCY candidates preserved. Frozen workers, independent
challenge and isolated API pass; production unchanged. [WG40 audit](../audit/wg40-biib-legal-apellis-scope.md).

## Final release gate

All 440 accounted for; 419 update contracts or individually documented repairs;
successive real filings across required families; complete frozen comparison;
current UI/API/database and operational UAT; user approval. No production,
scheduling, merge, push or deployment before that gate.
