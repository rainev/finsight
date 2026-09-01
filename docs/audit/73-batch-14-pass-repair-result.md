# Batch 14 Practical-Materiality Pass Repair Result

Status: **user confirmed on 2026-08-30**. The user authorized a repair review of
the nine confirmed Batch 14 Conditional companies. HCA and REGN are source-backed Pass repairs;
the other seven retain their material Conditional dependencies. No value changed.

## Before and after

| Outcome | Confirmed initial | Repaired final |
| --- | ---: | ---: |
| Pass | 1/10 — IDXX | 3/10 — HCA, REGN, IDXX |
| Conditional | 9/10 | 7/10 — TECH, BIIB, VRTX, INCY, GILD, BSX, MCK |
| Withheld | 0/10 | 0/10 |
| Numeric | 10/10 | 10/10 |

Every low/base/high value is byte-for-byte numerically unchanged. Only HCA/REGN availability,
method version, warning, reliability governance, and private materiality evidence changed.

| Ticker | Initial | Repaired | Low | Base | High | Reliability |
| --- | --- | --- | ---: | ---: | ---: | --- |
| HCA | Conditional | Pass | $113.68 | $341.89 | $666.52 | Low |
| REGN | Conditional | Pass | $520.07 | $775.66 | $1,201.75 | Low |

Low reliability remains because scenario movement is broad; it does not make the source bridge or
ordinary model Conditional.

## Why HCA now passes

- Full professional-liability reserve sensitivity: $1.464B.
- No-reserve base common equity: approximately $76.159B.
- Maximum bounded impact: **1.9223%**, below the governed 5% threshold.
- Base half-reserve impact: approximately 0.96%.
- Balance-sheet reserve is stable: $1.466B at 2025-12-31 to $1.464B at 2026-06-30.
- The filing-text evidence binds self-insured/insurance-subsidiary reserves and expected claim
  payments to the exact 10-Q document hash.

The existing 100%/50%/0% reserve sensitivity remains in the private scenarios. The repair does not
pretend the reserve is zero; it recognizes that the fully bounded effect is ordinary and immaterial
relative to common equity.

## Why REGN now passes

- Base common equity: approximately $81.349B.
- Acquired IPR&D: $228.9M, **0.281%** of base equity.
- Intangible-acquisition cash: $99.9M, **0.123%**.
- Contingent consideration: $67.2M, **0.083%**.
- Collaboration revenue is recurring and comparative: $3.392B prior H1 and $4.355B current H1.
- Five-year consolidated cash history is complete; current TTM cash margin is below the historical
  base, so the model does not rely on an optimistic current collaboration margin.
- Cash/securities, debt/finance lease, contingent claim, dual-class shares, and NCI/preferred
  absence all remain source-reconciled.

The consolidated FCFF route does not require an invented product-versus-collaboration cash split
when aggregate recurring history is already complete and the exceptional amounts are immaterial.

## Why the other seven remain Conditional

- **TECH:** pending $73 merger and up-to-$1B Wilson Wolf investment change the object.
- **BIIB:** partial-period Apellis acquisition and new financing lack comparable combined history.
- **VRTX:** Crinetics transaction and $4.5B financing commitment remain pending.
- **INCY:** Vega acquisition/contingent consideration and CMS/product normalization remain material.
- **GILD:** $11.318B acquisition cash, $12.15B IPR&D, and pipeline claims are material.
- **BSX:** Penumbra integration, claims, NCI, litigation, and restructuring remain material.
- **MCK:** opioid cash/reserve, NCI, acquisitions, and working capital remain load-bearing.

No new Withheld company was created and no recovery attempt was consumed.

## Independent challenge

- Luna High source challenge matched every HCA/REGN source row, period, unit, accession, document
  hash, narrative term, securities/debt/share item, and comparative history fact.
- Luna xhigh economic challenge recomputed every materiality ratio and confirmed the
  practical-materiality classification.
- The exact first public candidate exposed one Important issue: HCA's public complete-bridge
  reliability expected zero accounting impact while the private payload carried 1.9223%. The fix
  retains 1.9223% in private materiality metadata but uses zero public accounting impact because the
  bounded reserve is already inside the canonical scenarios. Public caps are now High and no
  `RELIABILITY_PAYLOAD_INVALID` fallback remains.
- Final independent verdict: no remaining Critical or Important finding.

## Determinism and verification

- Final repair A/B full-tree SHA-256:
  `e967d64bfc196244e6ed9d194b2f30121fe6ac9e2a5c5f3536a3a5c61d50c018`
- Generated-private tree SHA-256:
  `401b19cbbc9d842204f90b8e6a8ff920a830cb40d68cd21101dca1466a501873`
- Staged-public tree SHA-256:
  `d0d7bad5cf636c186d675352a91beff88c44b2cf36fd6ed0cdb44bc429d1744b`
- Focused Batch 14 initial/repair tests: `7 passed`.
- Full backend suite: `1,509 passed, 3 skipped, 1 warning`.
- Frontend production build: passed (`1,694` modules transformed).
- Isolated cumulative catalog: 140 artifacts, 50 available / 84 conditional / 6 unavailable.
- Catalog publication: 134 review-required / 6 withheld.
- Catalog artifact-tree SHA-256:
  `017527d69070b481067b14d0c627eca6cae853a8e5e9bb3e57c16084d1f21350`.
- Real FastAPI list: HTTP 200, count 140.
- Detail/catalog parity: 140/140; repaired Batch 14 stage parity: 10/10.
- Calculator GET: 140/140; default numeric POST: 134/134 HTTP 200; six prior Withheld
  return HTTP 400.
- All ten Batch 14 calculators use the operating family; private leaks: 0.
- API receipt SHA-256:
  `db0ce219d61de06cef9978b7aa11291c9b452bf2b436e2209a2cc8157c74ab2f`.

The real API used an isolated untracked catalog with `save=false`. Tracked serving artifacts remain
unchanged.

## Cumulative staged result

If confirmed, cumulative classification through 140 issuers becomes:

- Pass: **50/140**
- Conditional: **84/140**
- Withheld: **6/140**
- Numeric: **134/140**

## Confirmation and bookkeeping

The user confirmed the repair on 2026-08-30. HCA and REGN were removed from the Recovery Learning
Watchlist because they are now fully source-bounded Pass results. The watchlist contains 90 entries:
84 Conditional and six Withheld. Its SHA-256 is
`287c84ca89e9b7fac8c154877ef428002267fdc60c286a1d59c9a9fed724bb2a`.

The append-only cumulative withheld register remains byte-identical at ten entries and SHA-256
`0205878089044e64002b8e181821939c266681e5258b882d2749ef3d068ae109`.
Focused repair/watchlist/register verification passed: `13 passed`.

Do not start Batch 15, promote or activate a tracked serving catalog, merge, push, or deploy
without a separate explicit signal.
