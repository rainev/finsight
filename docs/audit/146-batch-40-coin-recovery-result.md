# Batch 40 COIN Recovery Result

Date: 2026-09-07
Status: verified recovery result; user confirmed.

## Exact result

The single authorized recovery attempt covered exactly COIN. The full Batch 40 denominator remains ten.

| Ticker | Initial | Recovery | Low | Base | High | Reliability |
| --- | --- | --- | ---: | ---: | ---: | --- |
| COIN | Withheld | Withheld | — | — | — | — |

Recovered Batch 40 counts remain Pass **0/10**, Conditional **9/10**, Withheld **1/10**, numeric **9/10**.

## Recovery decision

The missing July 30 Q2 earnings Exhibit 99.1 was recovered from the official SEC filing directory and hash-pinned. It
reports Q2 revenue of $1.220068B, subscription and services revenue of $555.145M, non-GAAP adjusted EBITDA of $207.8M,
and a GAAP net loss of approximately $359M. The non-GAAP amount was retained as context and was not substituted for
common earnings.

Five exact annual common-earnings periods and current TTM were retained, including all losses:

- 2021: $3.096958B
- 2022: −$2.624949B
- 2023: $94.752M
- 2024: $2.577755B
- 2025: $1.260327B
- TTM through June 2026: −$987.766M

The six-observation 25th percentile / median / 75th percentile is −$717.1365M / $677.5395M / $2.248398B. A private
residual-income challenge found positive diagnostics when the negative bear state was replaced with a 1% ROE floor, but
that floor is not source-backed and was rejected. It was not published.

The controlling filing also says some additional tax losses cannot be estimated beyond recorded accruals, while legal
and regulatory matters may create additional material period charges. No claim range was invented. This independently
prevents a finite official bear/base/bull range under the controlled policy.

Customer and crypto funding were kept outside issuer cash. The $13.152428B aggregate cash line reconciles exactly to
$8.614065B corporate cash, $275.815M restricted cash, and $4.262548B client custodial cash. Client custodial funds and
their liability match at $4.299190B; off-balance-sheet safeguarding assets and liabilities match at $245.9B. Crypto
collateral, lending receivables, borrowed crypto, and owned crypto remain separately traced rather than netted into free
cash.

COIN therefore remains withheld. Recovery requires source-bounded tax/legal/regulatory claim ranges and a specialist
crypto/customer-funding schedule that supports a finite through-cycle bear/base/bull range without converting customer,
stablecoin, collateral, or safeguarding balances into issuer cash.

## Verification

- Recovery candidates: `output/batch-40-recovery-run-e-20260907` and
  `output/batch-40-recovery-run-f-20260907`; all 21 files are byte-identical.
- Recovery report SHA-256: `d07a7a329f2daae0f7d56a95afcbb24209a3038b7dccc9bdaecce0cb21abd3f2`.
- Recovery tree SHA-256: `31bfa28b1b6def94cc28a4397bdbdbd0492a504fde59092dc854745068495089`.
- Recovered earnings-deck SHA-256: `e4e006081ccb34629e8104427874cdef7bd65808e2ad448f85a7c28ff3b40236`.
- Focused Batch 40 contract/history/recovery/calculator tests: **23 passed**.
- Complete backend regression: **1,678 passed, 3 skipped, 1 warning** (523.55 seconds). The warning is the existing
  Python `crypt` deprecation in passlib.
- Frontend production build: passed, 1,694 modules. No UI behavior changed in this recovery.
- The first independent challenge found that the recovery runner was recalculating unrelated TPL. The final runner now
  copies the exact approved initial bytes and case rows for all nine non-COIN issuers. A second challenge confirmed all
  nine are byte-identical to the approved Batch 40 Run-G and reported no remaining Critical, Important, or Minor finding.
- A separate Sol final verifier replayed the final COIN diagnostics, public contract, 400-company catalog, API receipts,
  and recovery boundaries and reported no remaining Critical, Important, or Minor finding.
- Isolated catalog: 400 companies — 116 available / 271 conditional / 13 unavailable; 387 review-required / 13 withheld.
- Catalog tree SHA-256: `acae1c6b6f3d0e25fbd68723bab7dd044acc145c3c8174a71c8d9475129eca40`.
- Catalog manifest SHA-256: `9c37cb0be8ec98853475f6b258b1f41abb38ade6a2776a1be259d9a7a10631b2`.
- Real API: 400 list entries, 400 detail/calculator GETs, 400 expected calculator outcomes, exact list/detail parity,
  zero private leaks, and zero forbidden serving imports.
- Calculator API receipt SHA-256: `742de0fd6d346d1535df228fc7492aa156d4d28c034d1955eed08521615fa763`.
- Exact API/import receipt SHA-256: `ca215621dfce003bb8bd017c67cf2628aad17427ec85b718daedfb333910e77a`.

## Confirmation boundary

Tracked serving artifacts remain unchanged. The user confirmed this recovery outcome. This recovery did not initiate or
modify the separately authorized Batch 41 work already present in the workspace. The confirmed watchlist now contains 284 entries (271 Conditional / 13
Withheld), and the cumulative withheld register contains 23 entries. Watchlist SHA-256 is
`54a9744a54435a0f44ba93c766be436374e6037d5b02b037f7cf092c1a5e950d`; withheld-register SHA-256 is
`d3d8601fcd7c7387622781a7777fae0436cb10171e01b454c73c94d780133992`.
Merge, push, and deployment have not been performed by this recovery.
