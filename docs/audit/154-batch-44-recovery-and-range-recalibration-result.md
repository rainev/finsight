# Batch 44 Recovery and Whole-Batch Range Recalibration Result

Date: 2026-09-07
Status: verified recovery/recalibration result; user-confirmed and recorded.

## Outcome

The authorized recovery covered BKR, AMCR and SW. AMCR and SW now have transparent Conditional Low baselines; BKR
remains Withheld. The whole-batch review also replaced full stacked-tail ranges with moderated multi-factor ranges while
preserving every existing base value and reported bridge.

Final Batch 44: **Pass 0 / Conditional 9 / Withheld 1**, numeric **9/10**.

| Ticker | Initial range | Final range | Final status |
| --- | ---: | ---: | --- |
| MPC | $27.75 / $260.61 / $658.03 | **$114.70 / $260.61 / $420.16** | Conditional Low |
| PSX | $7.69 / $80.02 / $203.25 | **$34.03 / $80.02 / $129.58** | Conditional Low |
| FANG | $68.23 / $195.34 / $320.40 | **$117.15 / $195.34 / $249.06** | Conditional Low |
| BKR | — | — | Withheld |
| AMCR | — | **$2.61 / $17.92 / $36.64** | Recovered Conditional Low |
| DOW | $0.00 / $14.15 / $61.21 | **$0.00 / $14.15 / $33.19** | Conditional Low |
| CTVA | $2.30 / $26.37 / $55.29 | **$10.13 / $26.37 / $38.70** | Conditional Low |
| APA | $0.00 / $33.40 / $73.81 | **$8.70 / $33.40 / $50.30** | Conditional Low |
| SW | — | **$0.00 / $9.00 / $27.96** | Recovered Conditional Low |
| XOM | $39.24 / $83.64 / $138.20 | **$56.17 / $83.64 / $106.65** | Conditional Low |

## Why the original ranges were too wide

The initial bear and bull cases simultaneously applied full historical cash-margin tails, growth tails, WACC tails,
terminal-growth tails, +/-1.5% share stress and scenario-specific operating claims. Those corners were useful stress
tests, but they overstated the probability that every independent adverse or favorable input would occur together.

The final policy keeps each base exactly unchanged. Bear/bull cash margin, growth, WACC and terminal growth use the
midpoint between the full tail and base; share stress is +/-0.75%. Reported cash, debt, NCI and bear claim stress remain
unchanged. This is a moderated multi-factor decision band—not a statistical confidence interval and not a one-variable
sensitivity. DOW and SW retain raw negative bear residuals privately and use an explicit public $0 limited-liability
floor.

## Recovery decisions

- **AMCR:** the first full combined FY2026 supplies reported revenue, OCF, capex, interest, debt and shares. The Low
  fallback uses its 7.587% current cash-conversion margin with a disclosed +/-15% margin band. Older Amcor history is
  context only; the result is not presented as an established post-Berry cycle.
- **SW:** FY2025 and June-2026 TTM are two current-company observations. Predecessor/partial years are excluded from
  calibration. The bridge deducts debt/NCI and includes explicit $10M/$5M/$0 governed preferred-claim stress because
  10,000 preferred shares are reported while exact economic rights are not filed. Closure/restructuring cash and short
  history keep the result Low and wide.
- **BKR:** Chart closed after the June balance sheet. The $210 cash per Chart share and $2B term loans are known, but
  total cash consideration, assumed debt/claims, post-close cash/debt and combined OCF/capex are not. Modeling only the
  known loans would materially understate the transaction, so BKR remains Withheld.

## Challenge and repairs

Three Luna High reviews challenged source recovery and scenario width. One proposed holding all non-margin assumptions
at base; another proposed midpoint moderation. Sol selected midpoint moderation because it materially improves usability
without falsely removing commodity, leverage, claim and dilution risk. The source reviewer independently replayed AMCR
and SW and accepted them only as explicit practical Low fallbacks.

The challenge repaired stale +/-1.5% public dilution text, SW's floor description and preferred-rights warning, removed
an unsupported reliability reason identifier, and restored the valid public reliability payload. No unresolved Critical
or Important implementation finding remains.

## Determinism and verification

- Final candidates: `output/batch-44-recovery-run-d-20260907` and
  `output/batch-44-recovery-run-e-20260907`; reports and all private/public artifacts are byte-identical.
- Recovery tree SHA-256: `cc1d6cac0b49d4ac7c2169e33f3aa952e69e4d80ce83a5879d7da83f12ea451e`.
- Recovery report SHA-256: `f5a5fa469141f2217f9b03412d37d6fa1293e26c48ad0e7dfa7d95f320e31df3`.
- Focused Batch 44 initial/recovery tests: **16 passed**.
- Independent formula replay: **27/27** numeric scenarios exact; all public reliability payloads are valid.
- Complete backend regression: **1,731 passed, 3 skipped, 1 warning**. The warning is the existing Python `crypt`
  deprecation in passlib.
- Frontend production build: passed, **1,694 modules**.
- Deterministic recovery catalog: **440 companies — 116 available / 303 conditional / 21 unavailable**;
  **419 review-required / 21 withheld**. All 430 predecessor artifacts and all ten final Batch 44 artifacts match
  exactly.
- Catalog artifact-tree SHA-256: `7a71520960ccab9f7d9b289526cea5aef91c455d08e3c99fb5843a43c63d3a04`.
- Catalog manifest SHA-256: `483b1a8963471eb9648b703e6886896e60ee58be3853edb7116d64c160173a0a`.
- Real cumulative API: **440/440** list/details and **440/440** calculator defaults, exact parity, zero private leaks,
  zero forbidden serving imports and no invalid reliability fallbacks.
- Calculator API receipt SHA-256: `2d2640f81b1b4ca34e8d5803ab174909bb59783a383894043e37d5e69fb5a21a`.
- Exact API/import receipt SHA-256: `f98ae2d089961b1cc83d2c1ca0da4ddcc65ab790906b4caa9dc745491943bd8e`.

## Confirmation boundary

The confirmed cumulative universe contains **440 companies: 116 Pass / 303 Conditional / 21 Withheld**, with
**419/440 numeric**. All ten Batch 44 issuers are recorded in the Recovery Learning Watchlist; only BKR is added to the
cumulative withheld register.

The user confirmed this exact result. The Recovery Learning Watchlist now contains **324** entries (**303 Conditional /
21 Withheld**) with SHA-256 `d8cbaee0fca4c4749da2da0bacbc20f282fed764bdf1f42db25325d4542dd111`.
The cumulative withheld register contains **31** entries with SHA-256
`93e91a447b0836f168ccc050165a01c1cba7613434f3ed45e6a559ee45345d22`.

Existing serving artifacts remain unchanged. Batch 45, merge, push and deployment remain untouched.
