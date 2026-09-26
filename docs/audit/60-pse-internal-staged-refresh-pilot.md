# Audit 60 — PSE internal staged-refresh implementation

**Status: stage-only software path verified; real new-filing pilot not complete.** Scope is AP, BPI, RCR, RLC. No external fetch, scheduler, Postgres/MinIO write, approval-state change, catalog activation, deployment, or price input occurred.

## What now works

- `backend/app/pse_valuation/internal_refresh.py` accepts pinned local reviewed-fact JSON receipts, checks dates, normalized units, consolidation scope, per-fact page, reviewer and versioned assumptions, then calls the existing FCFF, residual-income, distribution, or SOTP model. A missing critical fact or stale unreviewed benchmark holds only that issuer and preserves its active artifact.
- RLC's refreshed SOTP requires a property-by-owner carrying/fair-value bridge that reconciles to consolidated totals. The calculator now honors that ownership bridge; legacy active RLC calculations retain their existing flat-bridge path.
- `scripts/stage_pse_intrinsic_refresh.py` builds an isolated, immutable 282-entry candidate with unchanged inherited artifacts byte-identical to Batch 28. A private report records old/new base, material-move flags, holds, and the RCR-to-RLC dependency. The candidate is always provisional and never activation-ready by itself.
- The active pointer and manifest were read back unchanged after staging tests: SHA-256 `50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92` / `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7`.

## Verification performed

- Synthetic, explicitly test-only local receipts exercised all four model routes, the isolated CLI, deterministic twin catalogs, 282/282 catalog loading, real authenticated in-process FastAPI GETs (no token 401; token list/detail 200), legacy/new SOTP calculator parity, hold behavior, source-hash tampering, 20% attribution flag, and inherited-artifact equality.
- Focused internal-refresh tests: **17 passed**. Full backend suite: **469 passed, 1 existing `crypt` deprecation warning** with `PYTHONPATH=.:backend`. Frontend production build passed with the existing large-chunk warning.
- The complete browser journey was not exercised against this synthetic candidate. The API was exercised through FastAPI's real ASGI router, not an externally served instance.

## What remains unverified or unimplemented

No rights-cleared **new filing plus complete reviewer-approved fact/assumption receipt** was supplied for this run. Synthetic tests verify the runner, **not** a refreshed AP/BPI/RCR/RLC valuation. The existing AP FCFF bridge, RLC ownership split, RCR post-infusion payout and current discount choices still need source-backed reviewer decisions. Original filing bytes were not captured; JSON receipt SHA-256 is not an original filing hash. The local runner has no automated source discovery, Postgres/MinIO capture, or scheduler yet; enabling those requires a source-by-source rights basis and a separately scoped implementation. Existing public values remain unchanged.

**Next gate:** provide one permitted, reviewed real filing receipt for any pilot issuer and run a supervised staged cycle through the real API/page. Then extend to the other three routes; do not infer user approval, publication, or activation from this test-only verification.
