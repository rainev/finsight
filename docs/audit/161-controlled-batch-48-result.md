# Controlled Universe Reset Batch 48 Result

Date: 2026-09-11
Status: user-confirmed initial result; recovery pending.

## Outcome

Batch 48 processed exactly **10/10** frozen companies:

- **Pass: 0/10**
- **Conditional: 8/10** — FRT, UDR, VTR, DOC, WELL, KIM, CPT, IRM
- **Withheld: 2/10** — WY, EQR
- **Numeric: 8/10**

| Ticker | Low | Base | High | Result |
| --- | ---: | ---: | ---: | --- |
| FRT | $78.77 | $84.21 | $90.44 | Conditional Low |
| UDR | $29.57 | $31.61 | $33.95 | Conditional Low |
| WY | — | — | — | Withheld |
| VTR | $45.39 | $48.52 | $52.11 | Conditional Low |
| DOC | $20.63 | $22.05 | $23.69 | Conditional Low |
| WELL | $75.97 | $81.21 | $87.23 | Conditional Low |
| KIM | $21.49 | $22.98 | $24.68 | Conditional Low |
| EQR | — | — | — | Withheld |
| CPT | $76.80 | $82.14 | $88.26 | Conditional Low |
| IRM | $77.65 | $83.01 | $89.16 | Conditional Low |

## Practical valuation policy

The eight numeric REITs use the public model identity `affo_dcf`. Cutoff-safe issuer guidance or current specialist
metrics are reduced by reported or peer-bounded recurring-capital needs. The public range is deliberately moderated:
the base normalized AFFO per share is held fixed while the discount rate changes from 9.75% to 9.25% to 8.75%; growth,
terminal growth and the eight-year horizon remain fixed at 2%, 2% and eight years. Property capitalization is not
presented as NAV and is not blended into the primary value.

Important issuer treatments:

- FRT: base cash flow deducts the August $460M exchangeable notes' $14M annual coupon and half the maximum exchange
  dilution. Full-effect and no-effect cases are retained privately; no refinancing or capped-call benefit is invented.
- UDR: the reported H1 AFFO-to-FFOA conversion bounds recurring capital.
- VTR and KIM: missing exact current AFFO is bounded by the reported recurring-capital ratios of Batch 48 peers.
- DOC: reported H1 AFFO capital expenditure is applied to current FFO as Adjusted guidance.
- WELL: reported recurring capex, tenant improvements and lease commissions reduce Normalized FFO. The current outlook
  already follows the reported Canadian-note and announced/closed acquisition activity.
- KIM: the reported FFO numerator and diluted denominator use the issuer's as-converted preferred treatment; the
  preferred liquidation claim is not deducted a second time.
- CPT: current guidance incorporates the California sale; intended debt repayment is not surplus value. The excluded
  $53M settlement is deducted once as $0.503716 per diluted share.
- IRM: issuer-reported AFFO already deducts recurring capital, so it is not deducted twice.

## Why WY and EQR are withheld

- **WY:** the current timber trough produces a raw bear residual of **-$3.93/share**. The former display floor of $0 was
  rejected. Land/standing-timber economics, harvest-cycle normalization, reforestation/environmental obligations and
  preferred/NCI scope do not yet support a positive finite public range. The $0/$5.20/$16.56 diagnostic remains private.
- **EQR:** shareholders approved the AvalonBay merger on August 12 and closing was expected August 17. At the August 14
  cutoff, standalone EQR guidance had been withdrawn but the combined Vivmark object had not closed. The cutoff issuer
  remains EQR/CIK 0000906107; later VMRK identity data is not substituted.

## Challenge and repairs

Three independent Luna High reviews challenged source identity, recurring-capital arithmetic, model suitability,
event treatment, public identity, calculator behavior and range calibration. Sol resolved every finding:

- FRT note coupon/dilution was bound into base arithmetic and reconciled explicitly.
- Stacked flow/cost/rate ranges were replaced by a moderated rate-only public range.
- The honest `affo_dcf` identity and `reit_affo_exact` calculator lane replaced the generic FFO label.
- The calculator now locks already-deducted recurring capital, normalized AFFO, the horizon, terminal growth and
  one-time claim adjustments; only AFFO growth and discount rate are editable.
- WY's legal zero floor was removed and the result withheld.
- EQR and WY expose neither a numeric range nor a calculator; their Low reliability label is subordinate to the
  explicit Withheld publication state.

No Critical, Important or Minor implementation finding remains in the final candidate.

## Determinism and verification

- Final candidates: `output/batch-48-history-run-p-20260911` and `output/batch-48-history-run-q-20260911`; all private,
  public and report files are byte-identical.
- Report SHA-256: `54a03164392ae10e154621820aa2ac446efd7f08cb2ae1707a9fcb682d073132`.
- Candidate tree SHA-256: `d32526e38eaf08c0a76f4e676a0cc660fdc859d6c2d470e1e570a76cf27727ac`.
- Focused Batch 48/calculator tests: **15 passed**.
- Final complete backend suite: **2,341 passed / 3 skipped / 0 failed**.
- Frontend production build: passed (`1,694` modules transformed).
- Immutable cumulative catalog `US-RESET-2026-08-14-B01-B48-INITIAL-1.0` was built twice with byte equality:
  **480 companies = 116 Pass / 338 Conditional / 26 Withheld**, numeric **454/480**. Manifest SHA-256:
  `ac2e9bb662b8b66dc36c5127376329ae6f67be343116ce4c3c815d59b7d5492a`; artifact-tree SHA-256:
  `6036cbbe651da2714c42dca5b3e7c78f61d77599b77410e23ef51347c0e8226f`.
- Real isolated API: **480/480** list/detail exact catalog parity, **480/480** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Official receipt SHA-256:
  `beefbdccf8c04e899a2df6ca01e92ff60ce3a8b717f7d06eaed44fa41610f452`; calculator receipt SHA-256:
  `f4e30952e6d68580aabf72d2485912b349b56b53108e2668a6db49b6f5ccedf9`.

## Boundary

Serving artifacts, the Recovery Learning Watchlist and cumulative withheld register remain unchanged. Recovery for WY
and EQR, confirmation bookkeeping, Batch 49, merge, push and deployment require separate authorization.

The user confirmed the initial Batch 48 result. Batch 48 remains **0 Pass / 8 Conditional / 2 Withheld**, with
**8/10 numeric**. The isolated 480-company candidate remains **116 Pass / 338 Conditional / 26 Withheld**, with
**454/480 numeric**. WY and EQR have not yet received their one authorized recovery attempt, so watchlist and cumulative
withheld bookkeeping remain deferred until that recovery result is separately confirmed.
