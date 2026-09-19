# WG36 — HON separation, split and acquisition scope

WG35 narrow result confirmed by the user. WG36 uses cached evidence only within
Batches 01–44. HEAD at start: 4fa0a64. Existing changes and histories preserved.

## Bounded audit and specification

Reference: current continuing-company cash, debt, ownership and shares must share
one economic scope after a separation and acquisition.

| Gap | Severity | Firsthand evidence | Required behavior |
|---|---|---|---|
| WG36.1 | P0 | Note 1 actual close June 27 versus report June 30; event June 29 | Bind actual accounting close and event date separately |
| WG36.2 | P0 | Note 1 says all share/per-share amounts retrospectively split-adjusted | Never apply split again to reported shares |
| WG36.3 | P0 | Note 3 retains Aerospace assets, liabilities and operations in these statements | Block continuing HON FCFF until distributed/retained scope reconciles |
| WG36.4 | P0 | Johnson Matthey close after period; purchase allocation pending | No acquisition-price value or invented funding/cash/earnings |
| WG36.5 | P0 | Quantinuum deconsolidation and trademark terms are separate mechanisms | Keep their cash, NCI and conditional terms nonadditive |

Reuse existing hashed narrative extraction, NCI proof, immutable recipes and
two-worker verifier. Add a versioned separation evidence evaluator and wire it
into the existing blocked-source flow. Prove source identity/units/scope and
adversarial failures; independently challenge the economics; replay frozen
HON/HCA and the isolated API. Current state: source classification and blocking
safeguards verified and user-confirmed 2026-09-18. Full HON reconciliation remains
incomplete. All P0 economic gaps above remain explicit requirements.

## Firsthand source findings

Controlling HON 10-Q `0000773840-26-000124`, filed 2026-07-23, report date
2026-06-30; structural SHA256 `48d7e6c225caf649da4a8f2d9784adbcb893224df737d729288b90ae6d3f204a`;
HTML SHA256 `eb593f0a7cac1222711b4c73acc5dbc2a32ffba8c62e059ad972ce191c57c074`.

Note 1 states actual close June 27; June 29 distribution/reverse split is in the
next fiscal quarter although the reporting convention says June 30. All shares
and per-share figures are already retrospectively split-adjusted. Cover shares
316,940,010; Q2 diluted weighted average318.6M and H1 average319M must remain
distinct. No second split is performed.

Reported balance/flow ledger remains the combined pre-distribution company:
cash8751M, long-term debt31510M, short borrowings2478M detailed/2500M rounded,
ordinary NCI320M; H1 OCF626M and capex538M. Raw debt alternatives are preserved
without selecting a new bridge total. Quantinuum is separately deconsolidated:
retained investment7525M + removed NCI703M − removed net assets1599M = gain6629M;
the IPO delivered no cash contribution/distribution to HON. Cash deconsolidation
623M is not a second Aerospace cash distribution or acquisition payment.

The Aerospace license promises1125M total:18.75M initially due within five days
of distribution plus59 monthly18.75M payments. Receipt status is unknown. The
50M nonrenewal and250M specified termination reimbursements are conditional
terms; neither is promoted to a current liability. Tax/forecast overlap remains
unreconciled, so no receivable/PV/cash credit is invented.

Johnson Matthey closes July17 for1750M net of acquired cash; allocation is
pending for September30 reporting. The cached parent filing does not reconcile
actual funding sources, cash paid, post-close balances or acquired FCFF.

## Cached HONA corroboration and limitation

HONA 10-Q `0002089271-26-000021`, raw HTML SHA256
`beea9795ec3c68142ab8f8fdde42336f991abeddf42bf60b9ec6f94d055301d9`, was also
inspected read-only. Its June27 carve-out reports assets19371M, liabilities24994M,
cash1057M, long-term debt15853M, NCI74M, H1 OCF346M and capex260M. Note1 warns
allocated corporate expenses may differ from independent-company costs; H1
corporate allocations are294M. Centralized cash pooling, parent transfers and
intercompany eliminations prevent treating parent-minus-carve-out amounts as an
automatically reconciled current continuing-parent state. These are corroborating
audit observations, not model inputs or a new HONA valuation. The full closing
and post-acquisition bridge remains required.

HON's statement reports15835M pre-separation financing. HONA describes16B of
notes,6B of notes distributed and9.1B cash proceeds delivered to HON as partial
consideration, with the parent note guarantee released upon distribution.
These distinct amounts must not be added to cash again or used to manufacture
the Johnson Matthey funding split. They corroborate why full closing entries
and intercompany eliminations are still required.

## Retained results

| Company | Historical low / base / high | Change | Current result |
|---|---|---|---|
| HON | 60.78533467481803 / 149.61398945604896 / 277.0528047042256 | 0 / 0 / 0 | Implementation gap; continuing scope unresolved |
| HCA control | 113.67603706327972 / 341.89411295994046 / 666.5180777852703 | 0 / 0 / 0 | Existing current runoff blocker preserved |

Both retain Low reliability. Historical parity is not endorsement of a current
post-event HON valuation. No numeric successor or unavailable conversion.

Frozen real two-worker report:
`output/us-refresh-group-verification/d5938f131de280cedaf05795fc7f3e1dbcda5ea70dc298c169ec31d7fd5d281c/report.json`.
File SHA256 `d868d6f59111ef27b9596741d7a25a3e8fa2ef6a450873e0d2ad6344f62a19bc`;
implementation `c98903d60b95128a4665f621329b2683ad7167a4db768e5d463855a9ead21527`;
policy `df93d51533e7ac78b8051d34590756a9a82d7583306c32e86c9d7c626647797d`.
Narrative file SHA256 `1d7aeb2ce46bd06da72fac88e98321ad059fa80753091f05fe4f9576c7d84bd1`.
Focused25 pass. Final broad802 pass, one existing Passlib crypt warning,282.61s.
Independent Luna High review passes14 dedicated checks and finds no material
correction; primary verified its financial observations. See
[review](wg36-independent-review.md). Isolated API receipt
`output/us-refresh-runtime/wg36-blocked-preservation-api-evidence.json` SHA256
`2485fac105ab8df4ce84104d8963768844c15339ab43251c5327c0039b243fce`
verifies440 records and detail/calculator parity for HON/HCA/MCK/LHX/INTC/JBL.
No UI or saved-run behavior changed; browser and new database writes not repeated.

Final register:440 companies,419 recipes,282 compiled instructions,137 coding
gaps,196 financial flags,168 source flags,434 current-version rechecks,21 prior
unavailable,0 current full numeric source-bound and0 successive-period proofs.
Flags overlap. Current code/source report is a diagnostic blocked result, not
release readiness. Historical values and production artifacts remain unchanged.

## Following group, not started

WG37 can inspect the exact closing agreements and financial exhibits referenced
by cached submissions: HON June29 8-K `0000773840-26-000084` and July23 8-K
`0000773840-26-000120`. No acquisition was performed in WG36. Bounded retrieval
of these filings and directly relevant linked exhibits requires separate user
authorization. Their existence does not promise enough evidence for a new value.
