# Official Batch 04 history-backed promotion

**Confirmed and promoted:** 2026-08-26

## Official result

The user explicitly confirmed the Batch 04 history-backed shadow and authorized promotion.
Exactly ten public-safe artifacts were promoted to the default backend serving directory:

- Pass / Available: **4/10** — MCD, TJX, HD, ROST
- Conditional: **6/10** — F, GPC, HAS, LOW, NKE, MGM
- Withheld: **0/10**
- Reliability: **0 High / 0 Medium / 10 Low**

Five tickers were newly added: F, GPC, HAS, NKE, MGM.

Five existing serving artifacts were replaced: LOW, MCD, TJX, HD, ROST.

No Batch 05/06 artifact, watchlist entry, frontend data file, merge, push, or deployment was
changed.

## Promotion controls

- Confirmed source report SHA-256:
  47cc8b20102597b60cb1ee9109b375d171603bc169cdf814e1d136232d94b969.
- Promotion receipt SHA-256:
  7e5eed40f99fe63230ff32b6a6648f61cda74945b46ad4f81eb077a74feaee77.
- The ten promoted files are byte-identical to the confirmed run-e candidate.
- All unrelated backend serving artifacts remained byte-identical.
- Existing target files were backed up before replacement under:
  output/batch-04-history-promotion/official-20260826/backup/.
- Machine-readable receipt:
  output/batch-04-history-promotion/official-20260826/promotion-receipt.json.

## Verification

- Promotion command isolated test: passed.
- Complete backend suite after promotion: **1,270 passed, 3 skipped, 1 existing Passlib warning**.
- Frontend production build: passed; 1,695 modules transformed.
- Real default-serving FastAPI list: HTTP 200, count **211**, exact Batch 04 count **10**.
- Real detail endpoints: 10/10 HTTP 200 with exact promoted base/state/reliability.
- Real calculator GET endpoints: 10/10 HTTP 200 with exact base parity and locked historical
  periods.
- Private history leakage: zero.
- Server shut down cleanly.

## Gate

The history-backed Batch 04 result is **officially promoted and user-confirmed** in the local
default backend serving directory. This does not authorize or imply a Git merge, push, staging
deployment, production deployment, Batch 05/06 retry, or Batch 07 processing.
