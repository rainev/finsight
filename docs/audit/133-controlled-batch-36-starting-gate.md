# Controlled Universe Reset Batch 36 Starting Gate

Date: 2026-09-05
Status: **firsthand audited; implementation authorized and in progress**

## Exact denominator

The user explicitly authorized `Start Universe Reset Batch 36`. The denominator authority is
`backend/app/us_valuation/config/reset_batches_2026_08_14/batch_36.json`, SHA-256
`b6dc8108f78506039dd052d0b95e6cdfee02073ce87df95db2b1bb9b1f85900b`. It contains exactly ten
unique issuers in this order:

FISV, AMP, C, HIG, GS, MS, CB, ALL, COF, VLO.

Eight are Financials core issuers. COF is the consumer-finance boundary and VLO is the asset-backed
energy/refining boundary. The frozen model families are financial-equity for nine companies and
resource-cycle FCFF for VLO. Valuation date remains 2026-08-14.

## Predecessor and protected state

- The Batch 35 Sol repair is user-confirmed in Audit 132.
- Confirmed cumulative state through Batch 35: **350 issuers — 116 Pass / 224 Conditional / 10
  Withheld; 340 numeric**.
- Recovery Learning Watchlist: **234 entries — 224 Conditional / 10 Withheld**, SHA-256
  `0107c2acea1249c130790a73ead2f736c2bdb07c8bd49aa00967b048f771e80b`.
- Withheld register SHA-256:
  `7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`.
- Tracked serving catalog, frontend public data, and generated research remain unchanged and clean
  relative to the Batch 35 repair.

## Batch-specific gates

- FISV must be challenged as an operating payments processor versus a financial-equity issuer;
  classification metadata cannot choose an economically unsuitable residual-income model.
- AMP, C, GS, MS, and COF require equity-level capital/funding economics, period-specific preferred
  claims, and cutoff-safe financing events without an enterprise debt bridge.
- HIG, CB, and ALL require insurance reserve/underwriting-cycle treatment and parent-attributable
  earnings; ordinary reserve uncertainty may remain Conditional but cannot be silently omitted.
- COF's Discover combination requires comparable combined history or an explicit post-combination
  conditional bridge; predecessor and current shares/claims must not be mixed.
- VLO requires a refining-cycle cash model with complete current/noncurrent debt, commercial paper,
  finance leases, NCI/preferred claims, and bounded restricted cash.
- Every issuer receives a complete accepted/rejected cutoff-event receipt. Source packet,
  structural package, and primary-document hashes must be verified when valuation code runs.
- Public model identity, explicit availability, and calculator formula/defaults must remain separate
  and exact under the Batch 35 semantic contract.

## Gate

Proceed through the Batch 36 initial pass and stop after presenting Pass / Conditional / Withheld
for confirmation. Do not start recovery, Batch 37, tracked serving promotion, merge, push, or
deployment.
