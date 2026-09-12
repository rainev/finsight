# Controlled Universe Reset Batch 46 Result

Date: 2026-09-08
Status: user-confirmed initial result; superseded by the confirmed Conditional recovery in Audit 157.

## Exact outcomes

Exactly ten frozen utilities were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **6/10**, Withheld **4/10**, numeric **6/10**.
All numeric results are capped at Low reliability.

| Ticker | Model | Bear | Base | Bull | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| ATO | Utility residual income | $82.17 | $95.07 | $112.67 | Conditional Low |
| CMS | Utility residual income | $35.40 | $40.92 | $48.45 | Conditional Low |
| EIX | Intended utility residual income | — | — | — | Withheld |
| AES | Intended project-finance utility SOTP/FCFE | — | — | — | Withheld |
| PPL | Utility FCFE | $15.70 | $19.02 | $22.69 | Conditional Low |
| DTE | Utility residual income | $67.82 | $78.40 | $92.83 | Conditional Low |
| AEE | Utility residual income | $56.55 | $65.44 | $77.59 | Conditional Low |
| PCG | Intended utility residual income | — | — | — | Withheld |
| FE | Utility residual income | $15.94 | $18.47 | $21.91 | Conditional Low |
| SRE | Intended mixed-utility/infrastructure SOTP/FCFE | — | — | — | Withheld |

These are conservative decision baselines, not price predictions or recommendations.

## Models and historical layer

All issuers use source-linked FY2024, FY2025 and current TTM common earnings/equity. ATO correctly uses its September
fiscal year and nine-month comparative windows. Residual-income cases normalize sustainable ROE to the median of the
three observations and vary only cost of equity (9.5%/8.5%/7.5%) in the public bear/base/bull range.

PPL has a complete debt-funded-reinvestment history, so its FCFE route varies only the sustainable debt-funding share.
ATO and FE executed the same FCFE gate but produced nonpositive scenarios and therefore fell back to residual income.
CMS, DTE and AEE use residual income directly for explicit source reasons: CMS lacks comparable annual cash-capex
lineage and has a NorthStar scope change; DTE's capex line includes acquired businesses; AEE's debt-repayment lineage
changes while a prospective ATM/forward program can alter dilution. No EV debt bridge is used for any equity model.

## Why four companies are withheld

- **EIX:** wildfire liabilities, insurance/Wildfire Fund recoveries, regulatory recovery, preferred/NCI and Edison/SCE
  funding do not yet reconcile to one bounded parent-common-equity state.
- **AES:** consolidated OCF mixes parent recourse cash with nonrecourse project debt, $4.830B NCI and $3.052B
  redeemable/temporary equity. The credit-facility amendments do not supply the missing project/parent allocation.
- **PCG:** wildfire claims/recoveries and regulatory outcomes remain unbounded; $1.579B preferred, $252M NCI, a
  2.680B-versus-2.202B share conflict and incomplete current debt issuance prevent a reliable common-equity state.
- **SRE:** the pending 45% KKR infrastructure sale and Ecogas disposal interact with $3.308B temporary equity, large
  minority claims and regulated/LNG/merchant cash flows without a filed segment/transaction bridge.

Missing specialist detail is not the blocker by itself. These four remain withheld because the unresolved items could
materially change common value and cannot yet be bounded without guessing. Their private common-equity histories are
retained as diagnostics for one authorized recovery attempt after the initial batch is confirmed.

## Source and event evidence

All ten controlling filings are 2026-06-30 10-Qs filed by the valuation cutoff:

| Ticker | Accession | Filed |
| --- | --- | --- |
| ATO | `0000731802-26-000102` | 2026-08-05 |
| CMS | `0000811156-26-000028` | 2026-07-28 |
| EIX | `0000827052-26-000059` | 2026-07-30 |
| AES | `0000874761-26-000144` | 2026-08-04 |
| PPL | `0000922224-26-000044` | 2026-08-07 |
| DTE | `0000936340-26-000146` | 2026-07-28 |
| AEE | `0001002910-26-000023` | 2026-08-03 |
| PCG | `0001004980-26-000048` | 2026-07-23 |
| FE | `0001031296-26-000123` | 2026-07-28 |
| SRE | `0001032208-26-000045` | 2026-08-06 |

The source run captured 10/10 Companyfacts/submissions packets, 10/10 controlling structural filings, and 19 event
filings with 44 linked documents. Packet, structural, package and primary-document hashes are verified at runtime.
Fact-level periods—not unreliable wrapper periods—control selection. Serving artifacts were unchanged.

## Independent challenge and repairs

Three Luna High reviewers independently challenged the two source halves and the model/range/public behavior. Sol
reconciled their findings and repaired FE's parent-common TTM income to deduct NCI exactly once. The FCFE-first gap was
closed by executing FE's complete route and recording issuer-specific reasons why CMS, DTE and AEE cannot safely use
cash FCFE without inventing or mixing inputs.

The public schema uses `residual_income` for EIX/PCG and the supported `fcfe_dcf` formula family for the future segmented
AES/SRE owner-cash route; the private method retains their more specific project-finance/SOTP economic requirement.
Availability remains separate from model identity, and withheld calculators remain disabled.

No unresolved Critical or Important implementation finding remains in the candidate. The four withholding conditions
remain explicit economic uncertainties, not software defects.

## Determinism and verification

- Final candidates: `output/batch-46-history-run-b-20260908` and
  `output/batch-46-history-run-c-20260908`; reports and all private/public artifacts are byte-identical.
- Candidate tree SHA-256: `32d5108b8eb2521f5c2706373acc2f3d737accc2d387c865bca925f310278098`.
- Report SHA-256: `bc7940920f54c1c67722b25b213520d9550881eae7c9841512d4f83ae61cb3ad`.
- Focused Batch 46 tests: **8 passed**.
- Independent formula/public/calculator replay: **10/10 statuses and 6/6 numeric ranges exact**.
- Complete backend regression: **1,826 passed / 3 skipped / 0 failed**.
- Frontend production build: **passed** (`1,694` modules transformed).
- Immutable catalog: `US-RESET-2026-08-14-B01-B46-INITIAL-1.0`; two independent builds are byte-identical.
  Manifest SHA-256: `89e0936b89bdb8e273ca0db4428dcf5fb734d594a5ad282616310305f0b26e99`;
  artifact-tree SHA-256: `21f1462534444d982a43c3201487ec811f44270b3164528802618d5565dd0c0d`.
- Real isolated API: **460/460** list/detail exact catalog parity, **460/460** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Evidence receipt SHA-256:
  `2d0c89c784e880a45e8aa2f262577d533590d2fd7b10aaeb8e69dd51139729ca`; calculator receipt SHA-256:
  `c1270a9a71dcd9eede5dce8a7520e0478222dda40bb02a9ef48b500c510f34d0`.

## Confirmation boundary

The user confirmed this initial Batch 46 result. The provisional 460-company state is
**116 Pass / 319 Conditional / 25 Withheld**, with **435/460 numeric**.

EIX, AES, PCG and SRE are now eligible for one separately signaled recovery attempt. This confirmation does not itself
start that recovery or write final watchlist/withheld bookkeeping. The watchlist SHA-256 remains
`9cd45d793654ec4598332be78fea10923bc9debc12c2cb44fceba7505c9454c2`; the cumulative withheld-register SHA-256 remains
`93e91a447b0836f168ccc050165a01c1cba7613434f3ed45e6a559ee45345d22`. Existing serving artifacts remain unchanged.
Batch 47, merge, push and deployment remain untouched.
