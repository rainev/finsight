# Controlled Universe Reset Batch 45 Result

Date: 2026-09-08
Status: user-confirmed; confirmation bookkeeping verified.

## Exact outcomes

Exactly ten frozen utilities were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **10/10**, Withheld **0/10**, numeric **10/10**.
All results are capped at Low reliability.

| Ticker | Model | Bear | Base | Bull | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| AEP | Utility residual income | $62.45 | $72.29 | $85.73 | Conditional Low |
| ETR | Utility residual income | $42.94 | $49.72 | $58.96 | Conditional Low |
| ES | Utility FCFE | $28.38 | $40.65 | $45.33 | Conditional Low |
| XEL | Utility residual income | $37.83 | $43.78 | $51.90 | Conditional Low |
| SO | Utility FCFE | $28.66 | $41.96 | $50.18 | Conditional Low |
| LNT | Utility residual income | $33.28 | $38.51 | $45.65 | Conditional Low |
| D | Utility residual income | $29.37 | $33.98 | $40.28 | Conditional Low |
| PNW | Utility residual income | $54.82 | $63.44 | $75.19 | Conditional Low |
| WEC | Utility FCFE | $47.10 | $49.69 | $65.58 | Conditional Low |
| PEG | Utility FCFE | $43.65 | $44.90 | $50.27 | Conditional Low |

These are conservative decision baselines, not price predictions or recommendations.

## Model policy

Every issuer first runs the source-derived utility FCFE route:

`parent FCFE = parent share × [OCF − capex + debt-funding share × (capex + model income − OCF)]`.

Debt funding is derived from exact FY2024, FY2025 and June-2026 TTM issuance, repayment and short-term funding. Raw
ratios remain private; sustainable values are capped at 0%–100% and moderated between history and base. FCFE public
ranges vary only debt funding; growth, terminal growth, cost of equity, shares and parent allocation stay fixed.

When the executed FCFE route contains an unusable or degenerate scenario, the regulated-utility fallback values common
book equity and earnings through residual income without an EV debt bridge. Its public range varies only cost of equity
(9.5%/8.5%/7.5%); ROE, payout, terminal ROE, terminal growth and shares stay fixed. This produces practical ranges
without stacking independent tails.

## Important source and event treatment

- **AEP:** raw SEC submissions have an empty ticker list despite exact CIK/name/current filing. The raw file is preserved
  and an explicit CIK/name alias receipt is recorded. Capex sums construction, nuclear fuel and generation-facility
  acquisitions. The large multi-registrant filing required a bounded 300-second parser CPU limit.
- **ETR:** PP&E, nuclear fuel and other productive capex are summed. August $1.5B junior subordinated issuance remains
  hybrid funding context; excess historical financing is not recurring owner cash.
- **ES:** Aquarion closed at quarter-end and is already in reported cash/equity. Redeemable preferred/NCI is included in
  parent allocation; sale and offshore-wind charges remain comparability warnings.
- **XEL:** parent facts are selected over subsidiary registrant facts. Heavy current construction causes the dynamic
  residual-income fallback.
- **SO:** TTM common earnings are corrected to $4.741B by subtracting the reported negative NCI attribution from
  consolidated earnings. The value is anchored to June 30; August convertible financing is a revaluation trigger.
- **LNT/WEC:** separately hashed FY2025 structural packages supply current-concept annual capex continuity. LNT uses the
  dynamic residual fallback; WEC preserves preferred and minority interests in parent allocation.
- **D:** explicitly a **pre-merger baseline only**. NextEra consideration, synergies and post-close financing are excluded;
  no post-merger value is implied.
- **PNW:** raw financing exceeds measured reinvestment in 2025/TTM, making the FCFE range degenerate. The dynamic
  residual-income fallback retains the rejected FCFE evidence privately.
- **PEG:** parent equity components—common stock, treasury stock, retained earnings and AOCI—reconcile to total equity,
  with no parent-level NCI/preferred/temporary component. The funding-only range is narrower than full regulated/merchant
  nuclear uncertainty.

## Challenge and repairs

Three Luna High reviewers challenged source selection, utility economics, range calibration and public behavior. Sol
repaired AEP capex, SO parent earnings, FCFE common-income allocation, dynamic fallback selection, PNW's degenerate
range, PEG's claim-absence proof, explicit Conditional FCFE model identity, populated public scenarios, and a calculator
that edits the actual debt-funded-reinvestment driver. Residual ranges were changed to cost-of-equity-only scenarios.

No unresolved Critical implementation finding remains. D and SO retain explicit event-boundary conditions; PEG's narrow
funding-only band remains Low and must not be interpreted as low economic uncertainty. No issuer qualifies for Pass.

## Determinism and verification

- Final candidates: `output/batch-45-history-run-l-20260908` and
  `output/batch-45-history-run-m-20260908`; reports and all private/public artifacts are byte-identical.
- Candidate tree SHA-256: `ff2fd4733b88dc193a0f238eab6519ab38191773371d421e7cd4f9409349585a`.
- Report SHA-256: `a8e964d9e72d398ce3aeebba5ed7306b69805fdbe5c6ddc27139013a803e4621`.
- Focused Batch 45 tests: **9 passed**.
- Independent formula/public/calculator replay: **10/10 exact**, with correct directional overrides and no invalid
  reliability fallback.
- Complete backend regression: **1,799 passed / 3 skipped / 0 failed**.
- Frontend production build: **passed** (`1,694` modules transformed).
- Immutable catalog: `US-RESET-2026-08-14-B01-B45-INITIAL-1.0`; two independent builds are byte-identical.
  Manifest SHA-256: `f8ed878d680c92d76c8c003257dee540702986714e6ec715d6952d9f20a63b02`;
  artifact-tree SHA-256: `d81a1bac7aa011ea09f3271e493a92e7fc2ae6d66b4dbfceb7380b5d83f973be`.
- Real isolated API: **450/450** list/detail exact catalog parity, **450/450** calculator-default parity, zero private
  leaks and zero forbidden serving imports. The verifier explicitly accounts for the runtime-owned `catalog_version`
  and `freshness` fields. Evidence receipt SHA-256:
  `8991184126430999426cc5d8cd584df6a1425a119e9cfd56ba2289ccd2e30163`; calculator receipt SHA-256:
  `ab795a8c12fd07bc86e070953b85c35a7a1afbc67cd17c132ca514c84e5bb94a`.

## Confirmation and bookkeeping

The user confirmed Batch 45. The 450-company universe now contains **116 Pass / 313 Conditional / 21 Withheld**, with
**429/450 numeric**. All ten Batch 45 Conditional issuers were added to the Recovery Learning Watchlist with
`recovery_outcome=not_applicable`; direct Conditional results do not consume a withheld-company recovery attempt.

The Recovery Learning Watchlist now contains **334 companies**: 313 Conditional and 21 currently Withheld. Its SHA-256
is `9cd45d793654ec4598332be78fea10923bc9debc12c2cb44fceba7505c9454c2`. Because no Batch 45 company is Withheld,
no automatic recovery step is needed. The cumulative automatic-withheld history remains byte-unchanged at 31 entries;
its SHA-256 remains `93e91a447b0836f168ccc050165a01c1cba7613434f3ed45e6a559ee45345d22`.

Focused confirmation/bookkeeping tests: **15 passed**. Existing serving artifacts remain unchanged. Batch 46, merge,
push and deployment remain untouched and require separate authorization.
