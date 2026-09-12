# Controlled Universe Reset Batch 41 Result

Date: 2026-09-07
Status: verified and user-confirmed.

## Exact outcomes

Exactly ten frozen issuers were processed at valuation date 2026-08-14.
Pass **0/10**, Conditional **7/10**, Withheld **3/10**, numeric **7/10**.
All numeric results are capped at Low reliability.

| Ticker | Outcome | Bear | Base | Bull | Reliability |
| --- | --- | ---: | ---: | ---: | --- |
| APD | Withheld | — | — | — | — |
| AVY | Conditional | $46.47 | $113.02 | $184.81 | Low |
| BALL | Conditional | $4.78 | $21.27 | $40.35 | Low |
| ECL | Conditional | $33.75 | $78.52 | $132.02 | Low |
| EQT | Conditional | $2.71 | $15.02 | $58.88 | Low |
| HAL | Conditional | $10.44 | $24.57 | $41.92 | Low |
| IFF | Withheld | — | — | — | — |
| IP | Withheld | — | — | — | — |
| NUE | Conditional | $10.15 | $121.80 | $338.78 | Low |
| PKG | Conditional | $30.02 | $68.28 | $108.59 | Low |

These are conservative baseline decision ranges, not predictions, market-price targets, or recommendations.

## Source and model decisions

All ten controlling filings are cutoff-safe 10-Qs. APD, AVY, BALL, ECL, EQT, HAL, IFF, IP and PKG report through
2026-06-30; NUE's exact 52/53-week period ends 2026-07-04. The accessions are:

- APD `0000002969-26-000036`; AVY `0000008818-26-000131`; BALL `0001104659-26-090226`;
- ECL `0001628280-26-053886`; EQT `0000033213-26-000043`; HAL `0000045012-26-000061`;
- IFF `0000051253-26-000030`; IP `0000051434-26-000123`; NUE `0001193125-26-345891`;
- PKG `0001193125-26-339405`.

Numeric issuers use eight-year source-linked enterprise cash-FCFF with company-history or comparable-current cycle
normalization. Cash, debt, finance leases, NCI, pension/retirement claims, restructuring reserves and current shares are
reconciled once. Supplier finance and ordinary operating liabilities stay in working-capital/OCF economics rather than
being deducted again as debt.

- **AVY:** PP&E plus an explicitly estimated $27.8M annualized software/deferred-charge run rate are deducted. The
  $19.4M restructuring reserve is a finite claim. The opaque $427.9M retirement/other-liability line is not double
  deducted; its periodic cash remains in OCF and its uncertainty keeps the result Conditional.
- **BALL:** only 2025/current evidence governs the post-cups/post-Saudi packaging object. Issued shares less treasury
  reconcile to 264,605,826 at June; the later cover count of 264,703,357 is used. Pension/retiree liabilities are
  reserved once and Benepack/working-capital volatility remains material.
- **ECL:** June debt and cash already include $5B of CoolIT financing. Scenario cash deducts a 95%/100%/105% range
  around the reported $4.75B agreement price; the acquired operating asset is separately valued at private
  75%/100%/125% cost sensitivities. Neither sensitivity is described as reported value. The $334.4M pension deficit is
  reserved once.
- **EQT:** the June cash/debt anchor remains because exact post-event cash is unavailable. The July $115M debt repayment
  and $77M revolver-funded Blackline acquisition are recorded as base-value-neutral at-par exchanges; purchase price is
  not treated as intrinsic value. Five annual margins set the cycle range; the peak current TTM stays diagnostic. A
  conservative upper-bound PV covers Southgate/Boost total-cost ranges and two ten-year LNG-vessel leases.
- **HAL:** gross debt includes the $90M current maturity. The recovered Halliburton earnings exhibit records InformatiQ
  and the Aramco contracts as qualitative uncertainty because consideration and contract cash timing are not reported.
- **NUE:** cash, short-term investments, debt and NCI reconcile exactly. TTM capex of $2.841B exceeds the $2.5B FY2026
  guidance, proving the disclosed H2 program is covered. No West Virginia/NTS/Berkeley project value is added; unreported
  2027-2028 payment timing keeps the result Conditional.
- **PKG:** the current object includes Greif. Debt includes the $12.5M Valdosta build-to-suit financing obligation;
  pension/postretirement liabilities are reserved once. The 25-year minimum-volume shortfall begins in 2028, but its
  annual amount is unquantified and remains an invalidation warning.

## Plain withheld reasons

- **APD:** current and median cash FCFF are negative, recent project-heavy history is not a positive base, and up to
  $925M of project-exit cash remains. A positive value would require inventing unfinished-project economics or a future
  capex path.
- **IFF:** the income statement is recast to continuing operations, but the cash-flow statement still combines
  continuing and discontinued businesses. Continuing-company OCF and capex cannot be reconstructed without mixing the
  Food Ingredients/SCL sale perimeter or assuming pending proceeds.
- **IP:** total-company FCFF is positive, but only one complete post-DS-Smith year exists. GCF discontinued OCF is
  reported, while a complete continuing capex bridge is not; the EMEA separation and mill actions leave no comparable
  current-company cash base after $9.2B of debt.

## Independent challenge and repairs

Luna High audited all ten source packets, structural receipts, cutoff periods, share facts and event attachments. Luna
xhigh challenged AVY/BALL/ECL/APD/IFF/IP/PKG; a separate Luna xhigh challenged EQT/HAL/NUE. Sol replayed every formula,
bridge, source receipt and public contract after the repairs.

Resolved findings include the non-descriptive Halliburton Exhibit 99.1 filename, BALL/IP issued-versus-treasury share
reconciliation, AVY software reinvestment, ECL CoolIT cash/asset semantics and pension deficit, EQT event and commitment
cash treatment, HAL current debt, NUE capex coverage, PKG financing/pension claims, and the APD/IFF/IP withholding
rationales. The exact final candidate has no unresolved Critical or Important finding.

Remaining uncertainty is disclosed rather than hidden: EQT's total-cost reserve may double count incurred project spend;
NUE's 2027-2028 project timing and PKG's minimum-volume shortfall amount are unreported; ECL's final CoolIT settlement is
not yet reported. These limitations keep the numeric results Conditional Low.

## Determinism and verification

- Source replays A/B reused all ten issuers with zero network fetches.
- Structural replays A/B reused all ten wrappers with zero fetches or reparsing; both summary SHA-256 values are
  `a8effe41308c78e339317e0256714f5ea4f1e3d7c9f684f0caf0d2ac1e3cae56`.
- Final candidates: `output/batch-41-history-run-g-20260907` and `output/batch-41-history-run-h-20260907`; all 21 files
  are byte-identical.
- Candidate tree SHA-256: `60aef56241cf0ced3e51664b267d25f8b3410bf4933c80c5e4b58fd51881d142`.
- Report artifact SHA-256 (pre-confirmation result): `a1d1825266595ac1ef84c75eded8f6c7cf511608703710a158827d4837c483f8`.
- Focused Batch 41 contract/history tests: **10 passed**. Combined Batch 41 plus bookkeeping gate: **16 passed**.
- Complete backend regression: **1,822 passed, 3 skipped, 1 warning** (246.35 seconds). The warning is the existing
  Python `crypt` deprecation in passlib.
- Frontend production build: passed, 1,694 modules. No UI behavior changed.
- Isolated catalog: 410 companies — 116 available / 278 conditional / 16 unavailable; 394 review-required / 16
  withheld.
- Catalog artifact-tree SHA-256: `16517fe82c687b9d40f2d1ca31345d973d8455e36ea5d9eac9750cd9e3cae156`.
- Catalog manifest SHA-256: `efb490850b6f38d187a5adf018505edd55b12311b7d807b33a0647b01f52c341`.
- Real API: 410 list entries, 410 detail/calculator GETs, 410 expected calculator outcomes, exact list/detail parity,
  zero private leaks and zero forbidden serving imports.
- Calculator API receipt SHA-256: `8a0a3dd76f03594ad3ed79eec09c8b59a6ac93f6b480a4878980af081ae1f88e`.
- Exact API/import receipt SHA-256: `aacff20d2f2a0345ed1c831bc22b26920d92b275c3c59a1d666d91c0c3e3b1da`.

The first full-suite attempt was invalidated when the separately authorized COIN recovery updated bookkeeping during
test collection. The final candidates pin the confirmed post-recovery hashes and the complete suite passed afterward.

## Confirmation boundary

The confirmed predecessor contains 400 companies: 116 Pass / 271 Conditional / 13 Withheld. This Batch 41 candidate
would produce 410 companies: 116 Pass / 278 Conditional / 16 Withheld; numeric coverage would be 394/410.

The confirmed Recovery Learning Watchlist now has 291 entries (278 Conditional / 13 Withheld), SHA-256
`890c85240fffaff039ba136deb418c8273d77af3d0076be213f4cdcdb82a0889`. The cumulative withheld register remains 23 entries, SHA-256
`d3d8601fcd7c7387622781a7777fae0436cb10171e01b454c73c94d780133992`.

Tracked serving artifacts are unchanged. The seven direct Conditional Batch 41 issuers were added to the watchlist after
confirmation; APD, IFF and IP remain outside the cumulative withheld register pending a separate recovery signal. No
recovery, promotion, Batch 42, merge, push or deployment has been performed.
