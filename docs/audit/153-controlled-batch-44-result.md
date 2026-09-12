# Controlled Universe Reset Batch 44 Result

Date: 2026-09-07
Status: verified initial result; user-confirmed.

## Exact outcomes

Exactly ten frozen issuers were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **7/10**, Withheld **3/10**, numeric **7/10**.
All numeric results are capped at Low reliability.

| Ticker | Outcome | Bear | Base | Bull | Reliability |
| --- | --- | ---: | ---: | ---: | --- |
| MPC | Conditional | $27.75 | $260.61 | $658.03 | Low |
| PSX | Conditional | $7.69 | $80.02 | $203.25 | Low |
| FANG | Conditional | $68.23 | $195.34 | $320.40 | Low |
| BKR | Withheld | — | — | — | — |
| AMCR | Withheld | — | — | — | — |
| DOW | Conditional | $0.00 | $14.15 | $61.21 | Low |
| CTVA | Conditional | $2.30 | $26.37 | $55.29 | Low |
| APA | Conditional | $0.00 | $33.40 | $73.81 | Low |
| SW | Withheld | — | — | — | — |
| XOM | Conditional | $39.24 | $83.64 | $138.20 | Low |

These are conservative decision baselines, not price predictions or recommendations.

## Source and model decisions

All controlling filings are cutoff-safe for 2026-06-30; AMCR's controlling 10-K was filed on the cutoff date. Numeric
issuers use eight-year enterprise cash-FCFF with annual history, current TTM, explicit cycle scenarios, a current
cash/debt/claim bridge and latest cutoff-safe common shares. Raw negative equity is retained privately; DOW and APA use
an explicit public $0 bear under limited liability.

- **MPC:** current reported PP&E capex and consolidated debt/MPLX NCI are reconciled once. Future projects and capital
  return authorizations are not added.
- **PSX:** a targeted 2025 10-K package supplies exact 2023–2025 capex-and-investment lineage. WRB's move from
  proportionate to full consolidation keeps the result Conditional and is a hard future revaluation trigger.
- **FANG:** development capex is separated from property acquisitions. Cash interest, debt, large NCI, ARO and current
  shares are source-linked; repurchase authorization is excluded.
- **DOW:** continuing OCF, machinery capex, debt, NCI and environmental stress are kept separate. The 5.41M registered
  incentive-plan shares are covered by dilution sensitivity rather than assumed fully issued twice.
- **CTVA:** this is explicitly a current consolidated pre-separation value, not a post-Vylor value. Projected separation
  cash, debt and value are excluded; the result invalidates at separation.
- **APA:** a targeted 2025 10-K supplies the extension revenue lineage. Development capex excludes property acquisition;
  NCI is derived exactly from consolidated less parent equity. Savant/Uruguay remain pending.
- **XOM:** a separately hashed legacy-CIK 2025 10-K supplies 2023–2025 annual continuity for the July holding-company
  succession. The public filing URL uses the accession owner's legacy CIK; no reorganization value is added.

## Plain withheld reasons

- **BKR:** Chart closed after the June balance date. Two $1B term loans are known, but exact cash consideration, assumed
  claims, post-close cash/debt and combined operating cash flow are not in the controlling filing.
- **AMCR:** FY2026 is the first full post-Berry annual period; older periods are legacy or partial-combination Amcor.
  Acquired sales/EBIT do not provide a comparable multi-year combined OCF/capex cycle.
- **SW:** only FY2025 is a complete combined Smurfit Westrock year. FY2022–2023 are predecessor Smurfit and FY2024 is
  partial, so using them as one current-company cash cycle would splice unlike perimeters.

## Challenge, determinism and verification

Two Luna High reviewers challenged the source/model halves before and after implementation. Sol repaired fact-level
provenance in PSX/APA/XOM special annual rows, corrected the XOM public filing URL, and clarified AMCR's first full
post-Berry year. CTVA was retained only as an explicitly pre-separation consolidated baseline. No unresolved Critical or
Important finding remains.

- Final candidates: `output/batch-44-history-run-b-20260907` and
  `output/batch-44-history-run-c-20260907`; reports, private artifacts and public artifacts are byte-identical.
- Candidate tree SHA-256: `c4b3b988aa8b10862283a2e2427c51c19028cc4afb26ae1e48e8a258156e80fa`.
- Report SHA-256: `af8530bf8b549a4ef460315cbbd92d36f852eaa10b86c18860dda37ea7fd1ed8`.
- Independent formula replay: **21/21** scenarios exact; source cutoff/period checks and public leak scan pass.
- Focused Batch 44 tests: **9 passed**.
- Complete backend regression: **1,724 passed, 3 skipped, 1 warning**. The warning is the existing Python `crypt`
  deprecation in passlib.
- Frontend production build: passed, **1,694 modules**.
- Deterministic cumulative catalog: **440 companies — 116 available / 301 conditional / 23 unavailable**;
  **417 review-required / 23 withheld**. All 430 predecessor artifacts and all ten Batch 44 artifacts match exactly.
- Catalog artifact-tree SHA-256: `1cd5e2c6f412e74f3b2d4fc8dbffba3d77b9ce8d115a9b38ead36b6ef9a9813b`.
- Catalog manifest SHA-256: `3aada5766b0933074bae59b977eecb95e35f89b983c41903e061580aa25d8203`.
- Real cumulative API: **440/440** list/details and **440/440** calculator defaults, exact parity, zero private leaks
  and zero forbidden serving imports.
- Calculator API receipt SHA-256: `f20b8c2ca112b4687277ead928cc59d3f487a32292dedb8f94c68803c26aecc8`.
- Exact API/import receipt SHA-256: `eab1d9795644b7b6d297a9d7eb572a944e1285f943578f9574e2cc633800ee77`.

## Confirmation boundary

Batch 43 recovery and bookkeeping are user-confirmed. The confirmed predecessor contains 430 companies:
116 Pass / 294 Conditional / 20 Withheld. If this Batch 44 candidate is confirmed, the 440-company universe will
contain **116 Pass / 301 Conditional / 23 Withheld**, with **417/440 numeric**.

The user confirmed this exact initial result. The Recovery Learning Watchlist and cumulative withheld register remain
unchanged until the one-attempt recovery step is completed and confirmed. Existing tracked serving artifacts remain
unchanged. Recovery, Batch 45, merge, push and deployment remain outside this gate.
