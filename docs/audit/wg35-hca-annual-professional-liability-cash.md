# WG35 — HCA annual professional-liability cash evidence

WG35 narrow result subsequently user-confirmed; full HCA refresh remains open.
Started 2026-09-17 after WG34 narrow gate user confirmation. This is a bounded
annual-source/forward-overlap gate, not a completed HCA refresh or pipeline
release. Explicit public SEC authorization covered only HCA accessions
`0001193125-26-044769` and `0000950170-25-020134`, latest first, with the supplied
contact used only for SEC fair-access retrieval.

## Audit and bounded result

| ID | Severity | Acceptance | Status |
|---|---|---|---|
| WG35.1 | P0 | Two exact cutoff-eligible annual packages, complete hashes and offline parse | VERIFIED; CONFIRMATION PENDING |
| WG35.2 | P0 | Gross/current/noncurrent/reinsurance/net reserve rollforward | VERIFIED; CONFIRMATION PENDING |
| WG35.3 | P0 | Paid claims, provisions, OCF and forward-runoff overlap kept nonadditive | VERIFIED; CONFIRMATION PENDING |
| WG35.4 | P0 | Frozen workers, independent challenge, regression and isolated API | VERIFIED; CONFIRMATION PENDING |

## Acquisition and replay

Both authorized annuals parsed with the existing bounded SEC client and offline
Arelle. Network and offline-cache replay reports are byte-identical, SHA-256
`f53b7823f18483a46e6a6a995898f7f80f3aeb4b0f01e8c0ee91289cea74e9bd`.
Protected catalog/frontend hashes stayed unchanged. Download success alone was
not treated as economic validation.

| Accession | Report / filed | Raw HTML SHA-256 | Package manifest SHA-256 | Structural SHA-256 |
|---|---|---|---|---|
| `0001193125-26-044769` | 2025-12-31 / 2026-02-10 | `39c3e281a408cb4995981892498f21abdec254a592258e84a8583f5340e86d95` | `a67a58d87a514994f5dd4aeb4afddc42417a680974a8c15c1b0c439c38904617` | `ee9af162cad477a6ad03201ea6e87adfac78fe767e8f66e6a9b3161725c3c0bc` |
| `0000950170-25-020134` | 2024-12-31 / 2025-02-14 | `773b38e043c6b3a542a346d9cd884d44803a905a00644c6047a44257bacd2d75` | `c284960f2ca0baedc48cd0941361f6b865e2e5eb4ca2304a32ed3558aac749e2` | `ac487cef428b4e4ddf272cc0e6b84f4aa6012711e5a7d40815dc8b67c2182d58` |

## Exact source reconciliation

| Period | Gross reserve | Current | Noncurrent | Recognized reinsurance receivable | Net reserve |
|---|---:|---:|---:|---:|---:|
| 2024-12-31 | $2.131B | $587M | $1.544B | $80M = $45M current + $35M noncurrent | $2.051B |
| 2025-12-31 | $2.044B | $578M | $1.466B | $47M = $9M current + $38M noncurrent | $1.997B |
| 2026-06-30 current Q | not fully split | not tagged | $1.464B | not disclosed | narrative net total $1.996B |

Annual rollforwards close exactly:

- 2025: opening2051 + provision651 − paid claims702 − retroactive-reinsurance
  effect3 = ending1997M;
- 2024: opening2047 + provision627 − paid claims600 − effect23 = ending2051M;
- 2023: opening1983 + provision619 − paid claims550 − effect5 = ending2047M.

The latest annual also separates 2025 current-year/prior-year provisions525/126M
and payments12/690M. The older annual corroborates 2024/2023 rows exactly. Net
paid claims are550/600/702M for2023/2024/2025. Annual OCF is9431/10514/12636M.
Professional-liability premiums are not separately quantified.

Ordinary NCI remains a separate ownership stock:2834M at2023 year-end,3054M
at2024,3256M at2025 and3433M current Q. Annual NCI income849/897/998M and
distributions640/711/827M for2023/2024/2025 are owner-flow diagnostics, not
additional liabilities or reserve offsets. Current NCI is counted once.

Insurance investments remain dedicated, not surplus cash: 2024 total657M =
88M current +569M noncurrent; 2025 total588M =103M+485M; current Q total519M =
117M+402M. Coverage limits and reinsurance-retention thresholds are not reserve
claims. Historical47/80M recognized receivables are not current-Q cash or an
automatic current recovery.

## Economic conclusion and retained valuation

The annuals prove recurring provisions and paid claims are represented in
reported operating history. They do not provide the current reserve's multi-year
runoff schedule: HCA says timing beyond one year varies significantly, the
average resolution period is about five years, current Q gives only a573M next-
twelve-month aggregate/532M self-insured subset, and current current-reserve and
reinsurance splits are not tagged. Therefore historical claims are not deducted
again, but the bounded current noncurrent reserve sensitivity is not removed.

| Company | Retained low / base / high | Exact changes | Reliability |
|---|---:|---:|---|
| HCA | 113.67603706327972 / 341.89411295994046 / 666.5180777852703 | 0 / 0 / 0 | Low |
| MCK control | 477.99247723179093 / 849.8325771275278 / 1262.3562145555925 | 0 / 0 / 0 | Low |

HCA retains NCI3433M once plus noncurrent sensitivity1464/732/0M. Full1996M
net reserve, annual gross reserve, paid claims, dedicated investments and old
recoveries are not added/deducted again. `claim_adjustment=None`, no candidate,
no numeric/unavailable successor. Main HCA/MCK rows remain implementation_gap.

Private annual receipt
`output/us-refresh-runtime/professional-liability-annual-evidence/HCA.json`, file
SHA-256 `2b5aac06370343c959338af1b6871a21e7de6c9fee00517d47b433fa654e6723`,
receipt SHA-256 `2e70a5a9f81f94152c19955d6c62138250bba95b0e0524678d48f5ed5ac482d4`,
version `FINSIGHT-PROFESSIONAL-LIABILITY-ANNUAL-EVIDENCE-WG35-2`. The prior
pre-NCI receipt is retained immutably in evidence history.
Frozen repeated report
`output/us-refresh-group-verification/dd48c0a961567667903fcc89f541c2f37b53d0f6a6dc88ff200aaecdbaae31f5/report.json`,
file SHA-256 `ff65147b1cb20eb17ecff411d5041d0e9df77c208a97dd8a0bf32792d61cd992`;
implementation `74f170efbe3b4942dd9a435a0044147d995490a60960b3ec1e1764e4b2739aa1`,
policy `c82787f64a637d6371452a4454e895a4e5dfd5db2082a6edfeb6220e901bc05f`.

Independent Luna High challenge and final code review approve only this narrow
blocked result; final independent focused **22 passed in7.52s**, primary focused
**22 passed in9.50s**. Isolated real 440-company PostgreSQL API/detail/default-
calculator parity passes HCA/MCK/LHX/INTC/JBL/HON; receipt SHA-256
`c27b6b40dfe3fe1a4d71a93518d3789f55a05a0b66d4bd973b063f55105b8eaf`.
No UI/save/model behavior changed, so browser/save/activation/rollback is not
repeated or claimed. Final current-version broad **788 passed**, one existing
Passlib crypt deprecation warning, **348.79 seconds**. See
[independent review](wg35-independent-review.md).

Rebuilt register:440 companies,419 recipes,282 compiled instructions,137 coding
gaps,196 financial flags,168 source flags,435 needing current-version recheck,
21 prior unavailable,0 current full numeric and0 successive-period certifications.
Flags overlap and are not an overall completion percentage. Register JSON SHA-256
`12fed00b99741a832228b441ad91475830c314f4cfc8cb18cec5f34454cc463e`;
348 considered reports remain noncomposable release evidence. Diff check and pycompile pass; HEAD remains
`4fa0a64`. No production, schedule, merge, push or deployment.

## Following group, not started

Public annual/current evidence is exhausted for HCA's exact multi-year runoff.
Do not manufacture a schedule from the five-year average or keep adding duplicate
ledgers. Preserve WG35-S1 and move to the next source-supported unblocked stack;
HON's completed separation, shares/debt/cash and subsequent-acquisition scope is
the recommended WG36. No later group starts under WG35 authorization.
