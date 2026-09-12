# Batch 41 APD/IFF/IP Recovery Result

Date: 2026-09-07
Status: user-confirmed and recovery bookkeeping recorded.

## Exact result

The single authorized recovery attempt covered exactly APD, IFF and IP. The seven initially numeric Batch 41 artifacts
remain byte-identical to the confirmed initial candidate.

| Ticker | Initial | Recovery | Low | Base | High | Reliability |
| --- | --- | --- | ---: | ---: | ---: | --- |
| APD | Withheld | Conditional | $40.75 | $68.54 | $103.38 | Low |
| IFF | Withheld | Withheld | — | — | — | — |
| IP | Withheld | Withheld | — | — | — | — |

Recovered Batch 41 counts are Pass **0/10**, Conditional **8/10**, Withheld **2/10**, numeric **8/10**.

## APD recovery

APD recovered through parent/common-equity residual income rather than forcing a parent-funded FCFF or project SOTP.
Reported parent equity already includes recognized project-exit reserves, so NGHC nonrecourse debt and NCI remain inside
the parent-equity accounting perimeter and are not deducted again.

- Raw TTM parent earnings: **−$47.3M**.
- Reported FY2026 after-tax project-exit charge removed from recurring earnings: **$2.2366B**.
- Normalized TTM parent earnings: **$2.1893B**.
- Reported parent common equity: **$13.8838B**; current shares: **222,685,530**.
- FY2026 recognized project-exit reserve: **$696.8M**.
- Separate FY2025 reserve: **$89.9M**, excluded from the FY2026 comparison.
- FY2026 maximum cash exposure: **$925M**; maximum same-scope unrecognized excess: **$228.2M**.
- Bear/base/bull excess sensitivities: **$228.2M / $114.1M / $0**.

The first recovery candidate incorrectly reduced the FY2026 maximum by the $786.7M aggregate reserve, which included
the FY2025 program. The corrected candidate compares the maximum only with the $696.8M FY2026 reserve. No recognized
reserve is double-counted, and no purchase price, market price or unreported project value is used.

APD remains Conditional Low because future settlements, NGHC funding/offtake, remaining capex and normalized parent
earnings can still move value outside the range.

## Remaining withheld issuers

- **IFF:** total-parent residual income is mechanically calculable, but five recent annual parent earnings are
  $270M, −$1.871B, −$2.591B, $263M and −$361M; the historical median is negative. A private positive diagnostic would
  require a new unsupported earnings policy. Continuing income is separately reported, but continuing OCF and working
  capital are not. Food Ingredients/SCL assets ($4.840B) and liabilities ($1.170B) are now paired correctly; the separate
  CitraSource $44M/$3M held-for-sale group is excluded from that net. IFF remains Withheld.
- **IP:** 2025 parent earnings are −$3.516B and TTM parent earnings are −$3.438B. Current H1 positivity does not support
  a source-bounded ROE/payout path. Total-company FCFF of $982.7M remains diagnostic only because continuing capex after
  the GCF sale is incomplete and EMEA separation/mill actions remain unresolved. IP remains Withheld.

## Independent challenge

Three Luna xhigh reviewers independently challenged APD, IFF and IP. APD's reviewer found and rechecked the reserve-scope
repair; IFF's reviewer confirmed the corrected disposal-group ledger and negative history gate; IP's reviewer confirmed
the negative TTM earnings, invalid payout path and incomplete continuing-capex object. Sol replayed the formulas, public
calculator and protected-state checks. No Critical or Important implementation finding remains.

## Determinism and verification

- Recovery candidates: `output/batch-41-recovery-run-d-20260907` and
  `output/batch-41-recovery-run-e-20260907`; all 21 files are byte-identical.
- Candidate path/file hash-chain SHA-256: `e319dc0c5739af6934ce8c99fd087d14884c0c27d73d805375e3aa3271ca8cb1`.
- Recovery report SHA-256: `6f618b92cb90c26bae5a41dab8160e6efa7c895c5c4a2051f5b8beb384abd991`.
- Focused Batch 41 initial/recovery tests: **18 passed**; combined recovery/bookkeeping gate: **24 passed**.
- Complete backend regression: **1,839 passed, 3 skipped, 1 warning** (250.99 seconds). The warning is the existing
  Python `crypt` deprecation in passlib.
- Frontend production build: passed, 1,694 modules. No UI behavior changed.
- Isolated recovery catalog: 410 companies — 116 available / 279 conditional / 15 unavailable; 395 review-required /
  15 withheld.
- Catalog artifact-tree SHA-256: `581604e14c1e3573a40384baa8d11d6c248668d93bdfa46e611a45243df819be`.
- Catalog manifest SHA-256: `96c88602b8a48a27d08ce6ffd9139c00347aa61955c4d408cea3cb9abc20064e`.
- Real API: 410 list entries, 410 detail/calculator GETs, 410 expected calculator outcomes, exact list/detail parity,
  zero private leaks and zero forbidden serving imports.
- Calculator API receipt SHA-256: `af16d5ec1d20afbf49610b0e0c63f1878a20c05205be955be20f5b65bab5a696`.
- Exact API/import receipt SHA-256: `e19df59cf27dcc4205acbf371514041818106a3ca0ecfa221085e36fc7346e51`.

Tracked serving artifacts, the Recovery Learning Watchlist and cumulative withheld register remain unchanged. Only APD's
public artifact changes; the other nine public artifacts remain byte-identical to the confirmed initial Batch 41 output.

## Confirmation and bookkeeping

The user confirmed this recovery on 2026-09-07. The Recovery Learning Watchlist now contains 294 entries: 279
Conditional and 15 Withheld after recovery. APD is recorded as recovered Conditional Low; IFF and IP are recorded as
`withheld_after_recovery`.

The cumulative withheld register now contains 25 entries. IFF and IP each have exactly one consumed automatic recovery
attempt and point back to this audit. No valuation or serving artifact changed during confirmation bookkeeping.

- Confirmed Recovery Learning Watchlist SHA-256: `16e0c71cc8ab01daadae5f770f9e734ac9a8ff0f3d08ac4579905b8dfc2ae54e`.
- Confirmed cumulative withheld-register SHA-256: `215e5c09404de79cf9bdc390b7e086a61c9ea339f57c072501c3759ed752cff3`.
- Confirmation/bookkeeping verification: **24 passed** across the two register contracts and Batch 41 contract,
  history and recovery tests.
- Both immutable recovery reports retain SHA-256
  `6f618b92cb90c26bae5a41dab8160e6efa7c895c5c4a2051f5b8beb384abd991`.

Serving promotion, Batch 42, merge, push and deployment remain outside this confirmation.
