# Batch 35 Sol Audit Repair Result

Date: 2026-09-04
Status: **user-confirmed on 2026-09-04**

## Outcome

All six Important and three Minor findings from Audit 131 are repaired in a deterministic successor.
No company changed classification: the exact denominator remains Pass 0 / Conditional 10 /
Withheld 0 / Numeric 10, with all ten results capped at Low reliability.

| Ticker | Outcome | Low | Base | High | Change from confirmed Batch 35 |
| --- | --- | ---: | ---: | ---: | --- |
| WFC | Conditional | $38.90 | $59.47 | $79.37 | Value unchanged; exact model/calculator/source contracts added. |
| WMB | Conditional | $0.00 | $15.44 | $41.84 | Complete `$30.793B` debt bridge and bounded aggregate cash replace the overstated `$17.71` base. |
| AON | Conditional | $46.39 | $78.04 | $112.99 | Preferred uncertainty now maps maximum/base/zero to bear/base/bull. |
| SCHW | Conditional | $19.59 | $32.10 | $45.13 | Pre-cutoff note-interest sensitivity is explicit and applied. |
| GL | Conditional | $62.86 | $96.50 | $129.36 | Value unchanged; source/model/calculator contracts repaired. |
| AJG | Conditional | $62.38 | $104.22 | $148.38 | Preferred uncertainty now maps maximum/base/zero to bear/base/bull. |
| PNC | Conditional | $100.58 | $156.40 | $211.08 | Pre-cutoff note-interest sensitivity is explicit and applied. |
| RJF | Conditional | $51.15 | $81.35 | $112.13 | Value unchanged; source/model/calculator contracts repaired. |
| CFG | Conditional | $35.06 | $53.94 | $71.90 | `$400M` Series J proceeds/claim and `$27M` annual preferred dividend are included. |
| JKHY | Conditional | $26.91 | $42.97 | $59.75 | August cutoff disclosure is recorded; non-recurring deconversion revenue remains excluded from recurring earnings. |

## Repairs completed

- WMB now reconciles `$28.121B` noncurrent debt, `$2.197B` current maturities, and `$475M`
  commercial paper exactly once. Its `$203M` cash-plus-restricted-cash aggregate is ranged at
  `$0/$101.5M/$203M`. The signed Power Innovation JV remains explicitly event-conditioned.
- AON/AJG bear scenarios now deduct the largest governed preferred claim, while bull deducts zero.
  Their public warnings disclose the exact policy amounts and percentages.
- Nine public artifacts now identify `residual_income`; WMB identifies `fcff_dcf`. Conditional is
  preserved separately as availability, not used as a model name.
- Residual-income calculators now replay book value, ROE, payout, cost of equity, terminal ROE,
  terminal growth, and forecast years. WMB's calculator replays its exact faded-cash FCFF and bridge;
  its base discount rate is 9.5%, not the former fallback 10%.
- Every issuer now has an accepted/rejected cutoff-event receipt. The ledger contains five accepted
  and five rejected decisions, with accepted document hashes verified at runtime.
- PNC/SCHW note scenarios explicitly record a governed 21% tax rate and 0%/50%/100%
  proceeds-income offset. CFG's Series J issuance and JKHY's deconversion disclosure are traced.
- Source-packet, structural-receipt, package, and primary-document hashes are verified whenever the
  valuation runs. A tamper test proves altered input bytes fail closed.
- The Batch 35 and API tests now assert complete debt, adverse claim direction, event completeness,
  source-hash enforcement, model identity, exact calculator formula/defaults, and invalid terminal
  spreads. Locked source defaults submitted by the UI are accepted only when unchanged.
- The UI displays the actual model, formats ROE/payout/cost-of-equity assumptions as percentages,
  and preserves legacy Conditional labels. Audit 130's seven missing High-column cells were fixed.

## Independent challenge

Two independent Luna reviews challenged the exact repaired successors. The source/event reviewer
verified all source hashes, the 5/5 event ledger, WMB bridge, CFG preferred overlay, PNC/SCHW
interest arithmetic, JKHY exclusion, and AON/AJG claim direction. The model/public reviewer replayed
59 calculator overrides against the canonical residual-income/FCFF functions and verified model,
availability, sanitizer, API, UI, and legacy compatibility. Final disposition:
**0 Critical / 0 Important / 0 Minor**.

## Determinism and verification

- Final D/G: **21/21 files byte-identical**; full tree
  `557d24b89de43b266851db977795cf8b45ba1bc0d7b711ab1e03f1d8875dd17e`
- Final report SHA-256:
  `b4b80ade7d915479a2fe85be90225e70fc50d0a4f8302b361f69e4b7eb183b81`
- Event ledger: **10 screened — 5 accepted / 5 rejected**; summary SHA-256
  `01d8da458da017cb2a212d693d52566d6aee65dbb102ea0b496c6bb072a7040b`
- Focused Batch 35/calculator verification: **35 passed**
- Broader valuation/public-boundary verification: **137 passed**
- Complete backend suite: **1,601 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated cumulative catalog: **350** — 116 available / 224 conditional / 10 unavailable;
  artifact tree `65d2cd7964c7da9ca53cbd39fe0d9cab731190f7f6e6a25ec92d04b29bc8271c`
- Real API: **350 list, 350 detail, 350 calculator/default parity; zero private leaks**
- Batch 35 semantic API checks: **10/10 model identity, 10/10 exact defaults, WMB 9.5% base rate**
- Exact list parity: true; exact detail parity: **350/350**; forbidden serving imports: **0**
- Calculator/API receipt SHA-256:
  `ebe72e8f08f90c92f072446a49d0924a1aa7e1de40158c87cef5f37339254b71`
- Exact-list/detail/import receipt SHA-256:
  `17945fc885277701d9f0009fb6e610ad992f8cd2fc05ff8b2db54f6e3d8bed08`
- Catalog manifest SHA-256:
  `841d98873181f656eae1e9bce649de55a8da7dc686d5f1c9f51325d50528f821`

## Real browser evidence

- WFC displayed **Residual income valuation**, `$59.47` base, and ROE/payout/cost-of-equity fields
  as percentages; the residual-income calculator opened without an unsupported-input error.
- WMB displayed **Cash flow valuation** and the corrected `$15.44` base. Its calculator loaded a
  9.50% discount rate; changing it to 10.50% lowered the live base to `$10.44`.
- The legacy BRO Conditional artifact retained its prior Cash flow valuation label.

## Confirmation boundary

The Recovery Learning Watchlist remains exactly **234** — 224 Conditional / 10 Withheld — SHA-256
`0107c2acea1249c130790a73ead2f736c2bdb07c8bd49aa00967b048f771e80b`. The withheld register and
tracked serving catalog remain unchanged. The user confirmed this repaired successor with `y` on
2026-09-04; it now replaces Audit 130's Batch 35 values in the controlled cumulative state without
changing classifications or watchlist membership.

Batch 36, tracked serving promotion, merge, push, and deployment remain untouched.
