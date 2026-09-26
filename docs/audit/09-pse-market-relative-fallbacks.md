# Audit 09 — PSE market-relative fallback lane

**Implementation status:** Verified and user-confirmed on 2026-09-21. The confirmation covers staged Phase A.1 only;
it does not authorize activation, deployment, specialist-model recovery, or Phase B.

## Reference

The requested reference behavior is a practical screening estimate when specialist intrinsic inputs are incomplete,
similar in spirit to:

- GuruFocus GF Value, which combines historical multiples, past business performance, and future estimates:
  https://www.gurufocus.com/term/gf-value
- AlphaSpread, which publishes DCF and multiples-based values and combines them in its headline estimate:
  https://kb.alphaspread.com/hc/en-us/articles/18213235146513-What-is-Intrinsic-Value

FinSight will not copy either proprietary value or automatically blend a fallback into intrinsic value. The parity
target is narrower: publish a transparent low/base/high market-relative screen instead of returning no number.

## Ours today

- ✔ The public contract already has `market_relative_only` and a separate `market_relative` object.
- ✔ A pure comparable cross-check exists, but the Phase A pipeline only builds AP intrinsic and seven blocked artifacts.
- ✔ The API summary reads only `scenarios.base`, so a relative estimate would still appear null.
- ✔ The staged page renders only intrinsic scenarios or a blocked state; it has no market-relative presentation.
- ✔ Source-backed per-share metrics exist for all seven fallback issuers, although several remain review candidates.

## Reuse check

Reuse the existing artifact contract, immutable catalog, source references, comparable module, API routes, and staged
page. Add one versioned fallback-policy configuration; do not add a new service, database, model family, or data source.

## Flow

`specialist intrinsic blocked` → `load source-linked per-share metric` → `apply transparent policy band` →
`market_relative_only + provisional` → `serve low/base/high range` → `retain exact intrinsic limitations`.

## What backs it

- SCC, ACR, and PERC: reviewed legacy FY2025 EPS snapshots already used by the prototype.
- BDO: FY2025 annual-report EPS candidate (`PHP 16.28`).
- AREIT: Q1 2026 DPS candidate (`PHP 0.62`) annualized only for the yield screen.
- ALI: FY2024 EPS candidate (`PHP 2.70`).
- AC: annual-report EPS candidate (`PHP 64.77`).
- Every fallback retains the existing filing hashes and warns when the selected fact remains a review candidate.

## Gaps

- **P0 ✔ MR-01 — No numerical fallback:** seven issuers expose null despite sufficient evidence for a transparent
  screening-grade relative estimate.
- **P1 ✔ MR-02 — API summary gap:** list responses cannot expose the base relative estimate.
- **P1 ✔ MR-03 — UI gap:** the staged page would mis-render a nonblocked market-relative artifact as empty intrinsic
  scenarios.
- **P1 ✔ MR-04 — Semantics:** the estimate must remain `market_relative_only`; intrinsic limitations must remain
  visible and no value may be described as specialist intrinsic value.
- **P2 ⚠ MR-05 — Empirical calibration:** policy bands are initial screening conventions, not validated peer studies;
  issuer-specific peer calibration remains later work.
