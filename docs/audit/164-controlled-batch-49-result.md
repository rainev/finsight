# Controlled Universe Reset Batch 49 Result

Date: 2026-09-12
Status: independently verified candidate; user confirmation required.

## Outcome

Batch 49 processed exactly **10/10** frozen companies:

- **Pass: 0/10**
- **Conditional: 9/10** — REG, MAA, ESS, SBAC, ARE, BXP, PLD, CCI, EQIX
- **Withheld: 1/10** — AVB
- **Numeric: 9/10**

| Ticker | Low | Base | High | Result |
| --- | ---: | ---: | ---: | --- |
| REG | $53.84 | $57.56 | $61.82 | Conditional Low |
| MAA | $98.71 | $105.52 | $113.33 | Conditional Low |
| AVB | — | — | — | Withheld |
| ESS | $190.30 | $203.42 | $218.49 | Conditional Low |
| SBAC | $159.71 | $170.73 | $183.37 | Conditional Low |
| ARE | $74.97 | $80.14 | $86.07 | Conditional Low |
| BXP | $63.49 | $67.87 | $72.89 | Conditional Low |
| PLD | $76.77 | $82.06 | $88.14 | Conditional Low |
| CCI | $60.41 | $64.58 | $69.36 | Conditional Low |
| EQIX | $565.80 | $604.82 | $649.63 | Conditional Low |

## Practical valuation treatment

The nine numeric companies use `affo_dcf`. Issuer-reported AFFO is used directly for MAA, SBAC, CCI and EQIX. REG,
ESS, ARE, BXP and PLD use a transparent source-linked FFO-to-AFFO conversion. Normalized AFFO per share, recurring
capital, horizon, growth and terminal growth are locked; the public range varies only cost of equity from 9.75% to
9.25% to 8.75%.

Important issuer controls:

- REG: H1 AFFO/Core Operating Earnings conversion includes partnership scope and preferred warnings.
- MAA: Core AFFO already includes recurring capital; the $300M third-quarter bond maturity is a refinancing warning.
- ESS: trailing non-revenue capital is applied per diluted share.
- SBAC: parent-attributable AFFO already includes non-discretionary capital; Canada-sale tax and refinancing remain disclosed.
- ARE: reported five-quarter non-revenue capital bounds the FFO proxy; the August $1B junior-subordinated note pricing remains post-guidance financing context rather than invented proceeds.
- BXP: BXP-share tenant improvements/leasing and maintenance capital are divided by BXP Inc. diluted FFO, not Operating Partnership FFO. This challenge correction reduced the base from $70.93 to $67.87.
- PLD: H1 reported AFFO/Core FFO conversion retains development, land, turnover and co-investment warnings.
- CCI: continuing-operations AFFO follows the completed Fiber and Small Cell sale; sale proceeds are not added again.
- EQIX: reported AFFO includes recurring capital; large expansion capex, power, leases, foreign/JV scope and August debt issuance remain specialist warnings.

## Why AVB is withheld

AvalonBay shareholders approved the EQR merger on August 12 and closing was expected August 17. At the August 14
cutoff, AVB remained the legal issuer and only standalone operating guidance was available; combined Vivmark AFFO and a
final closing share/debt/cash bridge did not exist. No post-cutoff Vivmark facts or exchange-ratio value were substituted.

## Challenge and repairs

Three Luna High reviewers challenged sources, calculations, events, public identity and calculators. Sol repaired:

- BXP's denominator from Operating Partnership FFO to BXP Inc. common-share diluted FFO.
- Exact REG/ESS recurring-capital accession, document, numerator, denominator and formula evidence.
- Semantic supplement checks that bind the named metric row and low/high values.
- A real BXP extraction defect: oversized typed-member values now retain a bounded SHA-256 identity and explicitly empty typed members retain an `empty` marker instead of aborting or dropping the dimension.
- MAA's specific $300M maturity warning.

No unresolved Critical or Important finding remains. All nine companies stay Conditional Low because only current
issuer guidance, rather than long normalized AFFO history, anchors the baseline.

## Determinism and verification

- Final candidates: `output/batch-49-history-run-e-20260912` and `output/batch-49-history-run-f-20260912`; all private, public and report files are byte-identical.
- Report SHA-256: `680369362c54e41bb3187372ee11b7ea611f6da947813859e786772a7e92ecaa`.
- Candidate tree SHA-256: `6bc015d40acec0bf2b6d416a0ce84fce8741c0cde1a85b7eb84f2881b0d2e6f1`.
- Focused Batch 49 and typed-dimension tests: **13 passed**.
- Final complete backend suite: **2,358 passed / 3 skipped / 0 failed**.
- Frontend production build: passed (`1,694` modules transformed).
- Immutable cumulative catalog `US-RESET-2026-08-14-B01-B49-INITIAL-1.0` was built twice with byte equality:
  **490 companies = 116 Pass / 348 Conditional / 26 Withheld**, numeric **464/490**. Manifest SHA-256:
  `610dddd53ff0712073338b67e046b0d3565ff9968b85ae7ddd5b911c3f913fbb`; artifact-tree SHA-256:
  `6b76c610c54bc8e68863296148009b78a21f48e08abfd9b1c861838dff785898`.
- Real isolated API: **490/490** list/detail exact catalog parity, **490/490** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Official receipt SHA-256:
  `f7445180d84126046446666ef01eb249edb7b67f66e801c856612b474a9554b3`; calculator receipt SHA-256:
  `5986f1fdd487b0544d8b2a5ebab4f1d5a505f9a602e056327184aa420d276f42`.

## Boundary

Serving artifacts, the Recovery Learning Watchlist and cumulative withheld register remain unchanged. Recovery for AVB,
Batch 50, merge, push and deployment require separate authorization.
