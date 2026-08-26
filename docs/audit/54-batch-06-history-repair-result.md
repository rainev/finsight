# Batch 06 history-backed Pass repair result

**Valuation date:** 2026-08-14

## Outcome

- **Pass: 7/10** — BBY, DECK, TSCO, DRI, RL, MAR, CMG
- **Conditional: 3/10** — LEN, AMZN, YUM
- **Withheld: 0/10**

| Ticker | Prior base | History-backed base | Change | Final state | History treatment |
| --- | ---: | ---: | ---: | --- | --- |
| BBY | $61.11 | $49.82 | -18.5% | Pass | Five years; current TTM revenue repaired to $41.860B |
| DECK | $131.42 | $201.99 | +53.7% | Pass | Four years of seasonal footwear cash history |
| TSCO | $15.48 | $14.55 | -6.1% | Pass | Five years; supplier-finance/inventory stress remains source-backed |
| LEN | $52.73 | $128.40 | +143.5% | Conditional | Five years of common earnings; mortgage/land dependency retained |
| DRI | $107.96 | $150.30 | +39.2% | Pass | Five tightly grouped restaurant cash-history periods |
| AMZN | $42.29 | $42.29 | 0.0% | Conditional | Three years; negative current cash and AI-capex override retained |
| RL | $264.99 | $266.40 | +0.5% | Pass | Four years of apparel inventory/FX cash history |
| YUM | $89.88 | $89.88 | 0.0% | Conditional | Five years; disposal scope and FY-interest carry retained |
| MAR | $140.87 | $175.26 | +24.4% | Pass | Five years of asset-light/franchise cash history |
| CMG | $19.78 | $27.24 | +37.7% | Pass | Five years of owner cash using OCF less capex; no invented interest addback |

CMG is Medium reliability; the other nine remain Low. TSCO's history-backed bear value is positive
at $7.41, so its prior zero bear floor no longer applies.

## History and source controls

- Every profile uses three to five unique annual periods; annual periods and identical FY/TTM
  periods are deduplicated before percentile calculations.
- BBY TTM revenue is source-reconstructed as $41.691B + $8.936B − $8.767B = $41.860B.
- CMG uses a dedicated five-year owner-cash history (`OCF − capex`) because the filing has no
  nonzero interest-bearing-debt or finance-lease point fact. Missing interest is not set to zero.
- DECK and CMG debt absence, and all seven Pass issuers' preferred/NCI absence, are source-proven
  from the complete controlling structural filing.
- LEN uses five years of common-stockholder earnings but remains Conditional because history does
  not solve mortgage/land separation.
- AMZN retains the named AI/data-center capex override and negative current post-capex cash state.
- YUM retains disposal-group scope and annual-interest carry-forward as current material dependencies.
- Raw observations and source lineage remain private; only safe history metadata is public.

## Verification

- Independent Luna-XHigh challenge: **PASS**, no Critical or Important findings.
- Focused history/Batch 06/artifact suite: **122 passed**.
- Complete backend suite: **1,275 passed, 3 skipped, 1 warning**.
- Frontend production build: **passed**, 1,695 modules transformed.
- Candidate-a/candidate-b byte-identical tree SHA-256:
  `c436c161f190d8f3de65b618bfd23ff06be7a578844b3fc531165b433d9b67fd`.
- History repair report SHA-256:
  `c069f64d761e64361c6bc65ccdefbe0b5a9e36d93cffaace10a7bbfc7bf3bacb`.
- Real API: list/detail/calculator 10/10 HTTP 200; default parity 10/10; private leaks 0.
- API receipt SHA-256:
  `2edd34405e3c69a4d91ac098dbf646c88fe7cb7370744282d51d91d8e51ceaaa`.
- Batch 06 repair changed serving artifacts: **no**.

## Watchlist

BBY, DECK, TSCO, DRI, RL, MAR, and CMG were removed after verified source-bounded recovery. The
Recovery Learning Watchlist now contains 29 companies: 26 Conditional and 3 Withheld. Watchlist
tests pass 3/3; SHA-256 is
`e383d93b070f1e4e499cbeb39cd7971da4d1f7eb02e2a268f0919e7166aca33e`.

Batch 07, serving promotion, merge, push, and deployment were not started.
