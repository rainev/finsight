# Batch 34 Recovery Result

Date: 2026-09-03
Status: **user-confirmed on 2026-09-03**

## Outcome

One recovery attempt was run for all ten confirmed Batch 34 Conditional companies.

- Recovered to Pass: **2/10 — USB, BRO**
- Conditional after recovery: **8/10 — L, SPGI, NTRS, PGR, TRV, KEY, TFC, STT**
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Recovery treatment |
| --- | --- | ---: | ---: | ---: | --- |
| USB | Pass | $26.88 | $41.91 | $56.67 | Exact CET1/Tier 1/total-capital/leverage evidence and preferred claim closed the capital gate |
| L | Conditional | $61.27 | $94.25 | $124.30 | Statutory capital, reserve, parent-liquidity, and preferred-absence evidence still needed |
| SPGI | Conditional | $83.49 | $138.03 | $185.93 | A ratings/data and acquisition-history route remains to be source-bounded |
| NTRS | Conditional | $48.60 | $77.28 | $106.05 | Exact $884.9M preferred carrying claim used; post-cutoff redemption and custody economics remain |
| BRO | Pass | $27.28 | $44.96 | $63.79 | $25M NCI deducted; equity presentation supports zero preferred claim; ROE capped to history |
| PGR | Conditional | $43.72 | $80.70 | $121.92 | Reserve/catastrophe, statutory capital, and preferred-absence evidence remain |
| TRV | Conditional | $115.90 | $201.10 | $291.32 | Reserve/catastrophe, statutory capital, preferred absence, and July note event remain |
| KEY | Conditional | $10.46 | $16.71 | $22.95 | Capital evidence is bounded, but the September redemption remains post-cutoff and event reconciliation is open |
| TFC | Conditional | $32.22 | $49.88 | $67.05 | Capital and July note reconciliation remain provisional |
| STT | Conditional | $63.74 | $98.36 | $132.12 | Exact $3.559B carrying claim plus $500M Series L and ~$495M net proceeds used; capital gate remains |

All ranges are finite, ordered, and positive. No unavailable input was substituted with zero.

## What the attempt changed

- USB's controlling 10-Q reports 10.8% CET1, 12.2% Tier 1, 14.4% total risk-based capital,
  8.9% leverage, and a well-capitalized status. Its reported $6.808B preferred claim is already
  reconciled in the equity bridge, so USB is promoted to Pass with Low reliability.
- BRO's filing presents common equity and a separate $25M minority-interest component without a
  preferred claim. Recovery deducts the NCI, removes the speculative preferred placeholder, and
  preserves the history-bounded ROE; BRO is promoted to Pass with Low reliability.
- NTRS uses dimensional Series D/E carrying values of $493.5M and $391.4M, totaling $884.9M.
  Its October 1 redemption remains after the 2026-08-14 cutoff and is not removed.
- STT uses dimensional June 30 carrying values of $493M, $1.481B, $842M, and $743M, totaling
  $3.559B. The August 12 Series L event adds a $500M claim and approximately $495M net proceeds;
  proceeds are added to current equity and the preferred claim is deducted once.
- L, SPGI, PGR, and TRV retain bounded numerical estimates but still need issuer-specific capital,
  reserve, preferred-absence, or segment evidence before a Pass is defensible. KEY and TFC retain
  their cutoff event warnings and remain Conditional.

## Independent challenge

The first recovery challenge found two Important claim-selector errors and one regression: NTRS and
STT were using dividend-implied claims despite exact dimensional carrying values, and BRO had been
unnecessarily demoted by a speculative preferred placeholder. These were repaired. The final
challenge found **0 Critical / 0 Important** findings. One Minor note remains: STT's event row is
present twice in private context for traceability, but the $500M claim is used once in arithmetic.

## Determinism and real-consumer verification

- Final recovery G/H: 21/21 files byte-identical; report
  `2ae82e99152c91bae7edb4fe0b4b8f8ac816be9ebe15254087bf38d89b505c31`
- Recovery source audit receipt:
  `5b3ef8f8955522defe1ab75867e7cd429062f621cdffd97b875405f5fbd4d0a0`
- Focused recovery tests: **5 passed**
- Complete backend suite: **1,583 passed, 3 skipped, 1 warning**
- Isolated recovery catalog: **340** — 117 available / 213 conditional / 10 unavailable; artifact
  tree `dbbedc29bce1231b6323656d9d0391d9bb3a4a4f48a896646aee99be271f3748`
- Real recovery API: 340 list, 340 detail, 340 calculator/default parity; zero private leaks
- Exact detail/catalog parity: 340/340; forbidden serving imports: 0
- API receipt:
  `a1cbd31b81892fc77a184c73eae1dbe08ecc893e028975bc87851f7afb8b8168`
- Detail receipt:
  `0021d71aa245fbfb0d8a852b5c07269d4edd8a4e4277c2cc1b2fe2eece20363b`
- Catalog manifest:
  `30f0ce4e388e7275f4a877944f7cd9a2f98f15a2af7a785fc36ddc822b86e9a6`
- Confirmed watchlist remains **225** — 215 Conditional / 10 Withheld; SHA-256
-  `e80e4e627c054fbb4b1748e8e05a2b391e4401849dfede21f1aebab2c7763771`
- After confirmation, USB and BRO were removed from the Recovery Learning Watchlist. It now contains
  **223** entries — 213 Conditional / 10 Withheld; SHA-256
  `70b814e96e4d4e36a2bb45b0dca7d5ea1ee024eee09ee238218f52d82eebb294`
- Withheld register remains unchanged; SHA-256
  `7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`
- Existing tracked serving data remains unchanged.

## Confirmation gate

The user replied `y` on 2026-09-03. USB and BRO were removed from the Recovery Learning Watchlist,
reducing it to 223 entries — 213 Conditional and 10 Withheld. No withheld-register change was made.
Batch 35, serving promotion, merge, push, and deployment remain outside this gate.
