# Controlled Universe Reset Batch 09 Result

Status: **user confirmed on 2026-08-26**. This document preserves the initial result. CLX's later authorized recovery is recorded separately in Audit 60. No serving promotion, Batch 10, merge, push, or deployment was performed.

## Result

- Pass: **2/10** — BF.B, CL
- Conditional: **7/10** — ADM, STZ, KO, TAP, TGT, DG, GIS
- Withheld: **1/10** — CLX
- Numeric: **9/10**, all Low reliability

| Ticker | Outcome | Low | Base | High | Controlling filing / period |
|---|---|---:|---:|---:|---|
| ADM | Conditional | $7.54 | $22.94 | $60.84 | `0000007084-26-000042` / 2026-06-30 |
| BF.B | Pass | $4.33 | $8.80 | $25.86 | `0000014693-26-000024` / 2026-04-30 |
| STZ | Conditional | $36.06 | $93.37 | $160.11 | `0000016918-26-000029` / 2026-05-31 |
| CLX | Withheld | — | — | — | `0000021076-26-000034` / 2026-06-30 |
| KO | Conditional | $14.05 | $39.36 | $82.58 | `0001628280-26-050503` / 2026-07-03 |
| CL | Pass | $38.80 | $64.14 | $104.72 | `0000021665-26-000042` / 2026-06-30 |
| TAP | Conditional | $21.96 | $48.11 | $94.65 | `0000024545-26-000071` / 2026-06-30 |
| TGT | Conditional | $34.10 | $63.56 | $124.07 | `0000027419-26-000022` / 2026-05-02 |
| DG | Conditional | $44.73 | $117.00 | $181.76 | `0001104659-26-069205` / 2026-05-01 |
| GIS | Conditional | $8.51 | $26.43 | $50.95 | `0001628280-26-046466` / 2026-05-31 |

Values are USD per share baseline decision ranges, not predictions or recommendations.

## Key treatments

- BF.B preserves the frozen dotted ticker while explicitly mapping SEC `BF-B`; Class A plus nonvoting shares are reconciled to the total economic denominator.
- KO reconstructs current Q2 TTM flows directly because Companyfacts has no rows from the controlling accession. Cash, other short-term investments, separate marketable securities, notes payable, debt, and NCI are each included once.
- TGT retains its negative 2023 cash-FCFF observation; positive-only history filtering is not used.
- Supplier-finance and operating-lease balances remain inside operating cash conversion and are not bridge-debited again.
- ADM includes unrestricted debt securities, temporary equity, NCI, and debt while excluding restricted/margin cash.
- GIS removes disposal-group cash and includes continuing securities, notes payable, debt, leases, and NCI.

## Why CLX is withheld

The controlling 2026-06-30 Clorox 10-K package produced only two DEI facts and zero current financial bridge facts. Five years of older Companyfacts history exist, but cash, debt, claims, and diluted shares cannot be proven at year-end. Using the older Q3 bridge would violate the current-period source gate.

## Challenge and verification

The independent reviews found and resolved:

- omitted KO marketable securities and notes payable;
- DG finance-lease double counting;
- dropped negative TGT history;
- STZ commercial-paper omission and debt-basis inconsistency;
- TAP finance-lease double counting;
- omitted GIS notes payable and ADM short-term securities.

Final Luna XHigh verdict: **PASS; no remaining Critical or Important findings**.

- Focused Batch 09 tests: `7 passed`.
- Complete backend suite: `1,302 passed, 3 skipped, 1 warning`.
- Frontend production build: passed.
- Real FastAPI: list/detail/calculator parity 10/10; BF.B dotted path works; CLX calculator fails closed; private leaks 0.
- Candidate-e and candidate-f generated trees match: `31f675b5a677fab366895c9cfb0e10c882c559cd4924332a854e84717e7d0433`.
- Candidate-e and candidate-f public trees match: `9f0f5a518bff6823d805fb745d23b31d118008adc57830e1d2d1a886c223b9da`.
- API receipt SHA-256: `921d298c7543511591c44a27eb2bc7be1c973a38844ae51333e158a3c76b2f3e`.
- During valuation, challenge, replay, and API verification, protected serving artifacts and the Recovery Learning Watchlist remained unchanged.
- After confirmation, the watchlist contains 50 entries (46 Conditional, 4 post-recovery Withheld), SHA-256 `7bd753ab7df4644199ab09cb0b14c7f552ba73ca701059f0e4833204f6cc3bee`.

## Confirmation gate

The user confirmed the initial Batch 09 result on 2026-08-26. ADM, STZ, KO, TAP, TGT, DG, and GIS were bookmarked as direct Conditional results. The later CLX recovery is recorded in Audit 60. Batch 10 requires a later signal.
