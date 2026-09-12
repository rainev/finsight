# Controlled Universe Reset Batch 47 Result

Date: 2026-09-08
Status: user-confirmed initial result; superseded by the confirmed recovery in Audit 159.

## Exact outcomes

Exactly ten frozen utilities were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **7/10**, Withheld **3/10**, numeric **7/10**.
All numeric results are capped at Low reliability.

| Ticker | Model | Bear | Base | Bull | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| NRG | Intended merchant parent residual income | — | — | — | Withheld |
| ED | Regulated utility residual income | $58.83 | $68.05 | $80.63 | Conditional Low |
| EXC | Regulated utility residual income | $28.83 | $33.37 | $39.56 | Conditional Low |
| NI | Regulated gas/electric residual income | $20.11 | $23.28 | $27.60 | Conditional Low |
| CNP | Regulated utility residual income | $17.92 | $20.74 | $24.59 | Conditional Low |
| DUK | Regulated utility residual income | $69.98 | $81.00 | $96.03 | Conditional Low |
| AWK | Regulated water-utility residual income | $64.10 | $74.21 | $88.01 | Conditional Low |
| VST | Intended merchant parent residual income | — | — | — | Withheld |
| EVRG | Regulated utility residual income | $39.97 | $46.25 | $54.81 | Conditional Low |
| CEG | Intended merchant-nuclear parent residual income | — | — | — | Withheld |

These are conservative decision baselines, not price predictions or recommendations.

## Model policy and historical layer

The seven regulated utilities use exact FY2024, FY2025 and current-TTM parent/common earnings and equity. Sustainable
ROE is the median of those three source-linked observations. Public scenarios vary only cost of equity at
9.5%/8.5%/7.5%; payout, terminal ROE/growth, book value and shares remain fixed. No EV debt bridge is used.

Residual income is preferred because consolidated utility FCFE would mix material subsidiary-specific capital items:
electric/gas/steam scope for ED, nuclear and financing trusts for EXC, seasonal gas and NCI issuance for NI,
storm/recovery bonds for CNP, nuclear/project financing for DUK, water acquisitions/compliance capex for AWK, and
nuclear/deferred-fuel/coal transition for EVRG. Missing cash details are not replaced with zero.

## Why three companies are withheld

- **NRG:** retail and merchant generation, hedge/collateral cash, acquisitions, $650M preferred and recourse versus
  project/nonrecourse debt are not normalized into one parent-common earnings state.
- **VST:** merchant power/hedge earnings, generation/retail scope, $2.476B preferred, nuclear/coal/renewables cash and
  project financing cannot be represented by a regulated-utility model.
- **CEG:** merchant nuclear earnings, hedge/tax-credit effects, decommissioning trusts, PPAs, recent asset transactions,
  project debt and NCI are not normalized into one repeatable parent-common state.

All three have private parent-common earnings/equity diagnostics, but a numeric value would require a specialist
merchant normalization that the captured evidence does not yet support. They remain eligible for one recovery attempt
only after the initial result is confirmed.

## Sources and events

All ten controlling filings are 2026-06-30 10-Qs filed by the cutoff:

| Ticker | Accession | Filed |
| --- | --- | --- |
| NRG | `0001013871-26-000020` | 2026-08-04 |
| ED | `0001047862-26-000142` | 2026-08-06 |
| EXC | `0001109357-26-000080` | 2026-07-30 |
| NI | `0001111711-26-000088` | 2026-08-05 |
| CNP | `0001130310-26-000041` | 2026-07-28 |
| DUK | `0001326160-26-000040` | 2026-08-04 |
| AWK | `0001410636-26-000120` | 2026-07-29 |
| VST | `0001692819-26-000019` | 2026-08-10 |
| EVRG | `0001711269-26-000100` | 2026-08-06 |
| CEG | `0001868275-26-000104` | 2026-08-06 |

The run captured 10/10 Companyfacts/submissions packets, 10/10 structural filings and 31 event filings with 67 linked
documents. EXC exceeded the initial 300-second parser CPU ceiling; a 600-second bounded retry succeeded while reusing
NRG/ED and writing a new immutable structural root. Fact-level dates, not unreliable wrapper periods, drive selection.

## Independent challenge and repairs

Three Luna High reviewers independently audited two disjoint source groups and model/range behavior. Sol reconciled
their findings. The only Important implementation finding was the absence of an enforced finite `0 < parent share <= 1`
invariant; that hard check was added and tested. The merchant specialist route remains explicitly visible alongside the
generic public residual-income model sink while the value is withheld.

No unresolved Critical or Important implementation finding remains. A Minor diagnostic note remains: continue treating
structural top-level periods as non-authoritative; the implementation already records them with `used_for_selection=false`.

## Determinism and verification

- Final candidates: `output/batch-47-history-run-b-20260908` and
  `output/batch-47-history-run-c-20260908`; reports and all private/public artifacts are byte-identical.
- Candidate tree SHA-256: `f42e94921b6534a0c9098390efef7d6010fd9060b1cad77d9c5c13e8108e4027`.
- Report SHA-256: `17455670739f86ca707e9cbf1ce44aa0e6f8f17d9bde6a271b62f9431b4d628a`.
- Focused Batch 47 tests: **9 passed**.
- Independent formula/public/calculator replay: **10/10 statuses and 7/7 numeric ranges exact**.
- Immutable catalog: `US-RESET-2026-08-14-B01-B47-INITIAL-1.0`; two builds are byte-identical.
  Manifest SHA-256: `b2d49e1c56bf6c3364b7fc12f656dfec63243f9b342377f9469b81a2208ddf5a`;
  artifact-tree SHA-256: `a1d64e66380723e55fe7c65b6f4e644fee6d0504016d91921cd815bb639e20ad`.
- Frontend production build: **passed** (`1,694` modules transformed) after restoring the pre-existing npm-managed
  dependency layout disturbed by an unsuccessful offline pnpm invocation; no application source was lost.
- Real isolated API: **470/470** list/detail exact catalog parity, **470/470** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Evidence receipt SHA-256:
  `3da0a50cacd6c0468c0d6ce8bde5a2964d43c18dad712827aeed3d55ed5d66e9`; calculator receipt SHA-256:
  `f3f6e60de8a0792007edfef01ecd1733614c0f668d564f37b848d3954dabe5ff`.
- Complete backend regression: **1,889 passed / 3 skipped / 0 failed**. The three previously stale refresh-policy tests
  were aligned, with user authorization, to the compiler's current `compiled_source_validation_pending` behavior and
  passed before the clean full-suite rerun.

## Confirmation boundary

The user confirmed this initial Batch 47 result. The provisional 470-company state is
**116 Pass / 330 Conditional / 24 Withheld**, with **446/470 numeric**.

NRG, VST and CEG are now eligible for one separately signaled recovery attempt. This confirmation does not itself start
that recovery or write final watchlist/withheld bookkeeping. The watchlist SHA-256 remains
`b9d184c8b43631f4bdce076e912eb2bc296b6e2dc686ec10900e100592d64304`; the cumulative withheld-register SHA-256 remains
`93e91a447b0836f168ccc050165a01c1cba7613434f3ed45e6a559ee45345d22`. Existing serving artifacts remain unchanged.
Batch 48, merge, push and deployment remain untouched.
