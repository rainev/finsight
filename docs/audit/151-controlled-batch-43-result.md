# Controlled Universe Reset Batch 43 Result

Date: 2026-09-07
Status: verified initial result; user-confirmed.

## Exact outcomes

Exactly ten frozen issuers were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **7/10**, Withheld **3/10**, numeric **7/10**.
All numeric results are capped at Low reliability.

| Ticker | Outcome | Bear | Base | Bull | Reliability |
| --- | --- | ---: | ---: | ---: | --- |
| MLM | Conditional | $16.95 | $106.46 | $218.16 | Low |
| STLD | Conditional | $0.58 | $49.47 | $208.36 | Low |
| DVN | Withheld | — | — | — | — |
| COP | Conditional | $27.38 | $79.99 | $126.99 | Low |
| NEM | Withheld | — | — | — | — |
| MOS | Conditional | $0.00 | $11.76 | $58.95 | Low |
| CF | Conditional | $52.64 | $141.90 | $244.90 | Low |
| VMC | Conditional | $15.44 | $70.68 | $136.65 | Low |
| LYB | Withheld | — | — | — | — |
| LIN | Conditional | $51.76 | $122.99 | $217.58 | Low |

These are conservative decision baselines, not price predictions or recommendations.

## Source and model decisions

All ten controlling filings are cutoff-safe 10-Qs for 2026-06-30. Numeric issuers use eight-year enterprise
cash-FCFF with source-linked annual history, current TTM, explicit cycle scenarios, a current cash/debt/claim bridge,
and the latest cutoff-safe common-share denominator. Raw negative equity is retained privately; MOS alone uses a
public $0 bear under the limited-liability rule.

- **MLM:** the August 14 $5.5B acquisition-note issuance enters cash and debt once. Lhoist remains unclosed, so its
  operations, purchase value, synergies and the unfunded conditional facility are excluded.
- **STLD:** exact current and noncurrent debt are summed once. Negative nonredeemable NCI is not inverted into a
  claim; $143.259M redeemable NCI is deducted in every scenario.
- **COP:** a targeted 2025 10-K structural package supplies exact 2023–2025 productive-asset-and-investment capex.
  The July $1.7B disposition is recorded but neither proceeds nor disposed operations are mixed into the June bridge;
  pending Kirkuk economics are excluded.
- **MOS:** the current negative cash period remains visible. Base margin uses the conservative five-year annual-cycle
  median. The bridge includes short-term borrowings, current maturities and noncurrent debt/finance leases once;
  restricted debt securities are not surplus cash. The note offering/tenders settle after cutoff and remain pending.
- **CF:** only $662M unrestricted cash is used; restricted/VIE cash is excluded. $3.172B NCI is deducted once and the
  $170M litigation receipt is removed once from recurring cash-FCFF.
- **VMC:** current structural facts repair stale Companyfacts flow coverage. Restricted cash and the disposal note
  receivable are excluded; debt, finance leases, NCI and bear-only closure/environmental stress are separate.
- **LIN:** backlog is not capitalized. Debt, NCI and redeemable NCI are reconciled once; current acquisition spending
  is not extrapolated as ordinary recurring capex.

## Plain withheld reasons

- **DVN:** Coterra closed only seven weeks before quarter-end. Current cash flow combines old Devon with a partial
  combined period, so a multi-year combined-company cycle would require an invented pro-forma cash history.
- **NEM:** the NGM/Fourmile agreement includes a known $1.95B payment but also contributed project rights, assumed
  liabilities and confidential settlement terms whose common-equity impact is not yet finitely bounded.
- **LYB:** the European sale and refinery discontinuation changed the continuing company, while reported OCF remains
  consolidated. Captured evidence does not separate disposed cash flow from continuing cash flow.

## Challenge, determinism and verification

Two Luna High reviewers challenged source/model routing before implementation. Sol then checked current facts, model
direction, events, bridge arithmetic and formula replay. The challenge caught and repaired a $66.7M MOS current-debt
omission and replaced STLD's rounded debt total with exact current plus noncurrent carrying amounts. No unresolved
Critical or Important finding remains in the final candidate.

- Final candidates: `output/batch-43-history-run-g-20260907` and
  `output/batch-43-history-run-h-20260907`; reports, all private artifacts and all public artifacts are byte-identical.
- Candidate tree SHA-256: `5ec46ca5952cbd92c661c1834def5649933f26778be75d745fb050d14826907c`.
- Report SHA-256: `bd0a6b8337bed9adbe22433c12bb894d33992513c1181c9fa8be896506e6bdda`.
- Independent formula replay: 21/21 numeric scenarios exact; source cutoff/period checks pass; no private fields leak.
- Focused Batch 43 tests: **9 passed**.
- Complete backend regression: **1,709 passed, 3 skipped, 1 warning**. The warning is the existing Python `crypt`
  deprecation in passlib.
- Frontend production build: passed, **1,694 modules**.
- Deterministic cumulative catalog: **430 companies — 116 available / 294 conditional / 20 unavailable**;
  **410 review-required / 20 withheld**. All 420 predecessor artifacts and all ten Batch 43 artifacts match exactly;
  every source-audit path resolves.
- Catalog artifact-tree SHA-256: `38ac77162f464e661d97272404c3226d594b280d3a2506f3dbce26edfb2dec47`.
- Catalog manifest SHA-256: `5312da7559dd2155fe29f95811a94ccd9b35b91fb0d59535dbb7a98e2ef747e2`.
- Real cumulative API: **430/430** list/details, **430/430** calculator defaults, exact list/detail parity, zero private
  leaks and zero forbidden serving imports.
- Calculator API receipt SHA-256: `074f9540d91f74c3e7275d97b266087a46e37229116d71e23121c64cbd2cc0e1`.
- Exact API/import receipt SHA-256: `db18729fcc54c48d5e72bfb1253a8942c830384ccfb8e8f618a508259fc85a2e`.

## Confirmation boundary

Batch 42 recovery and bookkeeping are user-confirmed. The confirmed predecessor contains 420 companies:
116 Pass / 287 Conditional / 17 Withheld. If the verified Batch 43 candidate is confirmed, the 430-company universe
will contain **116 Pass / 294 Conditional / 20 Withheld**, with **410/430 numeric**.

The user confirmed this exact initial result. The Recovery Learning Watchlist and cumulative withheld register remain
unchanged until the one-attempt recovery step is completed and confirmed. Existing tracked serving artifacts remain
unchanged. Recovery, Batch 44, merge, push and deployment remain outside this gate.
