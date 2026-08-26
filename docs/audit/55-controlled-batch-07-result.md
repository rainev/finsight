# Controlled Universe Reset Batch 07 Result

Status: **user confirmed on 2026-08-26**. The six Conditional issuers were added to the Recovery Learning Watchlist. No Batch 08, serving promotion, merge, or deployment was performed.

## Denominator and result

Valuation date: `2026-08-14`. Exactly 10 frozen issuers were attempted once.

- Pass: **4/10** — EBAY, TPR, GRMN, DPZ
- Conditional: **6/10** — EL, BKNG, WYNN, LVS, TSLA, EXPE
- Withheld: **0/10**
- Numeric: **10/10**
- Reliability: **10 Low**

| Ticker | Outcome | Low | Base | High | Controlling filing / period |
|---|---|---:|---:|---:|---|
| EL | Conditional | $7.01 | $26.11 | $56.42 | `0001001250-26-000019` / 2026-03-31 |
| EBAY | Pass | $44.81 | $74.73 | $113.77 | `0001065088-26-000177` / 2026-06-30 |
| BKNG | Conditional | $197.40 | $391.67 | $593.16 | `0001075531-26-000037` / 2026-06-30 |
| TPR | Pass | $39.46 | $96.17 | $175.04 | `0001116132-26-000018` / 2026-06-27 |
| GRMN | Pass | $94.95 | $189.54 | $331.73 | `0001193125-26-322114` / 2026-06-27 |
| WYNN | Conditional | $0.00 | $108.29 | $398.97 | `0001174922-26-000055` / 2026-06-30 |
| DPZ | Pass | $86.16 | $211.48 | $343.22 | `0001286681-26-000035` / 2026-06-14 |
| LVS | Conditional | $0.00 | $50.82 | $106.64 | `0001300514-26-000085` / 2026-06-30 |
| TSLA | Conditional | $16.69 | $32.76 | $77.51 | `0001628280-26-049270` / 2026-06-30 |
| EXPE | Conditional | $260.69 | $546.99 | $1,173.78 | `0001324424-26-000053` / 2026-06-30 |

All values are USD per share and are baseline decision ranges, not predictions or recommendations. A zero casino bear endpoint is a limited-liability floor after a source-aware downturn stress; the recorded raw residual remains private.

## Historical layer

Every issuer used 3–5 unique cutoff-safe annual periods. Cash conversion is reconstructed from reported OCF, capex, and after-tax interest, except GRMN, which uses owner cash because the current filing proves no interest-bearing debt. GRMN's latest H1 values were reconstructed directly from its controlling filing because SEC Companyfacts had not yet incorporated that filing.

The shared revenue alias map now recognizes `RevenueFromContractWithCustomerIncludingAssessedTax`; this prevents WYNN from falling back to a stale 2018 revenue fact.

## Why six are Conditional

- EL: brand turnaround and restructuring make normalized margin recovery material.
- BKNG: deferred merchant bookings combine supplier funds and future company margin; the cash bridge therefore uses an explicit broad range.
- WYNN: casino-cycle downside, development spending, and negative book NCI attribution are material.
- LVS: casino-cycle downside plus Macao concession and Singapore expansion reinvestment remain material.
- TSLA: regulatory-credit dependence, AI/factory capex, product mix, and current share issuance remain material.
- EXPE: the supplier-versus-margin split inside merchant bookings is unresolved; nonredeemable NCI is deducted separately.

## Challenge repairs

The adversarial review initially rejected earlier candidates. The final candidate repairs include:

- EL debt includes $502M current plus $6.810B long-term debt.
- DPZ debt includes the $7.423M current component.
- TSLA uses the reported $9.342B debt-and-finance-lease aggregate and a current `xbrli:shares` denominator.
- EXPE deducts $1.262B reported nonredeemable NCI.
- Customer/merchant money is reserved from excess cash without subtracting the matching operating liability twice.
- TSLA regulatory credits reduce scenario cash by $1.052B / $526M / $0.
- WYNN and LVS include explicit near-zero casino downturn bear states.
- LVS applies $888M / $444M / $222M annual Macao reinvestment reserves; the roughly $3B already incurred for Singapore is not deducted again because reported capex is already inside cash FCFF.

Final independent verdict: **PASS; no remaining Critical or Important findings**.

## Verification evidence

- Focused tests: `19 passed`.
- Complete backend suite: `1,285 passed, 3 skipped, 1 warning`.
- Frontend production build: passed.
- Real FastAPI on `127.0.0.1:8765`: list 10/10; detail 10/10; calculator default parity 10/10; private leaks 0; directional checks passed.
- Candidate-g and candidate-h generated trees are byte-identical: `1aff32578be7bc285c62b96744eef0d0a7c0782e6c9ce9247464f4a3dbc22dd1`.
- Candidate-g and candidate-h public trees are byte-identical: `f2390c5aa0f8fa10a08131360432ce31d9bab526f3a57c5a15f0d4533a5c0cec`.
- API receipt: `09a96b226ededc0aad0e341ddfad1797532349c41fb8962708c10c30454d3313`.
- Protected serving hashes were unchanged by every Batch 07 run.
- Before confirmation, the Recovery Learning Watchlist remained unchanged at SHA-256 `e383d93b070f1e4e499cbeb39cd7971da4d1f7eb02e2a268f0919e7166aca33e`.
- After confirmation, the watchlist contains 35 entries (32 Conditional, 3 Withheld), SHA-256 `0b4b0e0703968fb7151b4b41deb7ed9028352c81eda75976981afb9701263d4c`.

## Confirmation gate

The user replied `y` and confirmed this classification on 2026-08-26. EL, BKNG, WYNN, LVS, TSLA, and EXPE are now bookmarked as direct Conditional results with `recovery_outcome: not_applicable`. Batch 08 requires a later, separate signal.
