# Controlled reset — Batch 01 result

**Verified:** 2026-08-20 (Asia/Manila)  
**Valuation date:** 2026-08-14  
**Batch:** AAPL, MSFT, CRM, ANET, WDC, DELL, JPM, BAC, NEE, O  
**Status:** verified — user confirmation needed  
**Serving promotion:** none

## Outcome first

- Processing completion: **10/10 for Batch 01; 10/500 cumulative**.
- Publishable numeric completion: **0/10 for Batch 01; 0/500 cumulative**.
- Outcomes: **0 numeric, 10 withheld, 0 invalid input**.
- Reliability counts for numeric values: **High 0, Medium 0, Low 0**.
- Every company remains visible in the denominator; no company was replaced or hidden.
- Old/generic pipeline numbers are retained only as private diagnostic comparisons. They are
  scrubbed from the controlled public artifacts and are not controlled-reset values.
- No serving artifact, frontend data file, Git branch, commit, merge, or deployment changed.

## Company outcomes

| Ticker | Controlled target model | Maturity | Outcome | Low | Base | High | Primary blocker |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| AAPL | mature operating FCFF with R&D treatment | Provisional | Withheld | — | — | — | Latest Products/Services economics, preferred/NCI evidence, and approved R&D life are missing. |
| MSFT | intangible-investment FCFF | Experimental | Withheld | — | — | — | No approved R&D life/amortization or governed AI-infrastructure reinvestment policy. |
| CRM | intangible-investment FCFF | Experimental | Withheld | — | — | — | Current segment economics, intangible/SBC treatment, and debt-step-up classification are incomplete. |
| ANET | profitable-growth FCFF with R&D sensitivity | Provisional | Withheld | — | — | — | Current bridge absences/conflicts plus growth/R&D limiting cases remain unresolved. |
| WDC | normalized cyclical FCFF | Experimental | Withheld | — | — | — | Three years do not prove a complete storage cycle; six bridge fields remain unresolved/rejected. |
| DELL | industrial FCFF + captive-finance SOTP | Experimental | Withheld | — | — | — | DFS equity/earnings/funding and industrial/finance claim allocation are unavailable. |
| JPM | bank residual income | Provisional | Withheld | — | — | — | CET1/RWA/buffers and verified average-common-equity treatment are incomplete. |
| BAC | bank residual income | Provisional | Withheld | — | — | — | Current preferred equity, CET1/RWA/buffers, and average-common-equity treatment are incomplete. |
| NEE | mixed-utility SOTP | Experimental | Withheld | — | — | — | Q2 facts, FPL rate-base economics, Energy Resources cash flows, and claim allocation are missing. |
| O | equity-REIT AFFO/NAV | Experimental | Withheld | — | — | — | Maintenance capex, property NOI/cap-rate evidence, and complete claims are missing. |

The complete blocker text and private diagnostic comparisons are preserved in
`output/batch-01-controlled/valuation-run-a/batch-report.md`.

## Source and structural evidence

- Exactly 10 immutable SEC submissions/Companyfacts packets were captured with the monitored
  contact supplied by the user.
- Packet audit: 10/10 ticker/CIK identities, 40/40 declared payload hashes, and 20/20 SEC-cache
  provenance records verified. SEC legal/display-name variants are preserved separately.
- Filing cutoff: no filing after 2026-08-14 appears in an eligible ledger.
- Companyfacts contains 307,194 fact-unit observations across the ten packets.
- Offline structural extraction ran only for the five FCFF cases with supported unresolved
  bridge fields: 5/5 parsed, zero failures, 19 decisions.
- Structural decisions: 1 accepted, 0 review, 10 rejected, 8 unresolved.
- The sole accepted decision is CRM's $664 million current finance-lease total from accession
  `0001108524-26-000127`. Exact-fingerprint promotion plus complete coverage proof clears the
  old bridge conflict, but CRM remains withheld because the selected software model is not
  mature and its load-bearing inputs remain incomplete.

## Shared model and policy changes

- Added fail-closed point-in-time specialist fact selection using filing date, period, form,
  accession, unit, and exact filing attribution.
- Fixed Realty Income's interim FFO route so missing property-sale gains no longer become zero.
- Added exact current structural-evidence promotion and safe Companyfacts/structural precedence.
- Corrected lease-total corroboration so carried-forward range midpoints are not treated as
  exact current split facts.
- Added input-explicit mechanical adapters for R&D capitalization, complete-cycle normalization,
  average bank common equity and capital-constrained payout, sum-of-parts reconciliation, AFFO,
  and property NAV. These helpers contain no issuer defaults and cannot fill missing evidence.
- The research basis remains aligned with CFA residual-income guidance, Damodaran's R&D/model
  selection resources, and Nareit's warning that AFFO requires recurring-capex and straight-line
  rent adjustments and is not standardized.

## Verification evidence

### Deterministic generation

- Structural runs A/B: 22 files each; identical tree hash
  `1575f0ab2116ea599a6a2362332f93591af86d0cd97963e36a6921387cd649f6`.
- Valuation runs A/B: 22 files each; identical tree hash
  `5c111bba5f880cc909b1deae36365dc3167377916e4ebe176af28f6e75d6e681`.
- Ten staged public artifacts re-sanitize to byte-equivalent canonical objects, expose no private
  source evidence, and contain null low/base/high values.

### Automated and prior-company replay

- Full backend suite: **1040 passed, 3 skipped**, one Passlib/Python `crypt` deprecation warning.
- Prior 106-candidate difficult-corpus replay after the shared lease correction:
  104 valid private, 94 source-verified, 1 Low numeric, 83 withheld, 6 build errors,
  4 source-integrity failures, 2 invalid inputs, 0 unsafe promotions, 0 public-contract failures.
- Two prior-corpus reports are byte-identical with SHA-256
  `db42ad8e0fe91487c44971ff0672145ef42b7b45cdd6ddcca036407c9b350f4c`.

### Real consumer path

- Real FastAPI listener started against the staged Batch 01 data root.
- `GET /api/us-valuations` returned 200 with exactly 10 items.
- Ten of ten detail requests returned 200 and agreed with the list: null base, withheld state,
  Low public safety label, and no private financial/source fields.
- Importing the FastAPI serving path loaded zero `arelle` modules.
- The server shut down cleanly.
- Browser UI check was explicitly skipped: frontend dependencies are absent (`vite: command not
  found`) and the route requires a local authenticated user. No UI code changed in this phase;
  installing unrelated dependencies or faking authentication was not substituted for evidence.

## Serving and approval boundary

The canonical serving hash remains
`34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.
There are no individually passing Batch 01 artifacts to promote. This report stops for user
confirmation; it does not authorize Batch 02, universe substitution, merging, or deployment.

