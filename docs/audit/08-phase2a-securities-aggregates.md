# Phase 2A securities and investment aggregates

**Verified:** 2026-08-20 (Asia/Manila)  
**Starting point:** `codex/period-aware-valuation-policy` at `27c2cda`, preserving Phase 1 evidence  
**Status:** Batch 2A verified — user confirmation needed; Batch 2B has not started.

## Reference

The approved Batch 2A requires canonical current, noncurrent, and total securities scopes; proof-bearing aggregate coverage; total-or-splits counted exactly once; annual/company-history ranges with lineage; peer ranges kept shadow-only; conflict/double-count protection; and a real distinction between `not_disclosed` and extraction failure.

The source denominator is the Phase 1 register: 64 `marketable_securities_noncurrent` blockers plus 12 `marketable_securities_current` blockers, or 76 overlapping field instances across 65 companies.

## Ours today

The implementation adds:

- a distinct `marketable_securities_total` normalized field;
- exact current/noncurrent coverage requirements and economic-scope validation;
- structured coverage lineage tied to accession, source period, concept, and context;
- total-or-splits reconciliation with the existing tolerance and one-split upper-bound checks;
- current-period-only corroboration, so annual/history totals do not conflict with or replace stronger current splits;
- proof-gated `not_disclosed`, requiring a complete search and searched-concept list;
- diagnostic/shadow authority for `sector_estimate`, plus bridge rejection as non-issuer-specific evidence;
- structural-shadow rules that reject a generic total under current assets as a comprehensive total;
- public-contract allowlists for the new private field and fail-closed reason codes.

Generic `MarketableSecurities` facts remain visible candidates, but they have no `covered_fields` or coverage proof and cannot clear the bridge.

## Reuse check and flow

The securities path reuses the existing debt/lease aggregate pattern in `bridge_policy.py`: exact coverage, source completeness, aggregate/component corroboration, and fail-closed conflicts. It does not add a parallel valuation model or change the 5%, 20%, or 40% reliability thresholds.

Data flow:

`Companyfacts / governed filing evidence / structural shadow -> scope-specific availability -> proof-bearing total candidate -> total-or-splits reconciliation -> bridge range -> public sanitizer`

Sector estimates remain in private diagnostics and fallback counts, but they no longer enter issuer cash-and-investments.

## What backs it

### Evidence audit

- ✔ 76 field instances: 64 noncurrent and 12 current.
- ✔ 17 complete securities blocker signatures.
- ✔ Audit classifications: 57 unresolved, 12 stale, 7 conflicting-candidate.
- ✔ No missing value was treated as zero.
- ✔ Only 13 companies had exact-period total/subtotal candidates; the candidates were not accepted as comprehensive totals by name alone.

Evidence:

- `output/phase2a-securities-audit-20260820/evidence-register.json`
- `output/phase2a-securities-audit-20260820/evidence-summary.md`
- `output/phase2a-securities-audit-20260820/accounting-challenge.md`

### Adversarial accounting gate

- ✔ Final Sol-high review: 12 of 12 invariants passed; no remaining P0/P1 finding.
- ✔ A disclosed split above a total blocks with `TOTAL_INVESTMENTS_AGGREGATE_CONFLICT`.
- ✔ The one-split check uses the existing inclusive tolerance.
- ✔ A historical/company-history total is ignored when stronger current split facts exist.
- ✔ Opaque coverage-source strings are rejected.
- ✔ Sector estimates are shadow-authority and rejected from bridge arithmetic.
- ✔ `not_disclosed` can only be produced from explicit complete-search metadata; the corpus correctly emits none because no such proof exists.

Evidence: `output/phase2a-securities-audit-20260820/implementation-review.md`.

### Automated and real-corpus verification

- ✔ Full backend suite: 996 passed, 3 skipped, 1 pre-existing Passlib/Python `crypt` warning.
- ✔ Final offline replays `-e` and `-f` match across all 189 JSON artifacts.
- ✔ Denominators: 106 input, 104 valid private, 94 source-verified, 6 build errors, 4 source-integrity failures, 2 invalid inputs.
- ✔ Public-contract failures: 0; unsafe promotions: 0.
- ✔ Serving artifacts changed: false; hash remained `34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.
- ✔ All 227 sector-estimate availability records have `authority=shadow`; zero retain production authority.
- ✔ No proof-bearing securities total was emitted from unverified cached candidates.
- ✔ Staged FastAPI list returned 94 items; ABBV, AMZN, APP, KO, and KVUE list/detail states agreed and exposed no private fields.

Final replay evidence:

- `output/phase2a-securities-replay-20260820-e/`
- `output/phase2a-securities-replay-20260820-f/`

## Outcome and remaining gaps

### Verified outcome

- ABBV remains the numeric no-regression control at `101.136738747441` per share.
- ABBV's cash-and-investments range remains exactly `$9.659B / $9.687B / $10.093B`.
- AMZN, APP, KO, and KVUE remain safely withheld.
- The only numeric result is ABBV.

Ten previous shadow numeric cases are now withheld because their bridge depended on peer-derived values: `BKNG`, `COHR`, `DXCM`, `EXPE`, `INTU`, `LOW`, `ROK`, `TEVA`, `TMO`, and `VRTX`.

This is a safety correction, not a recovery win. A finite peer range is not an issuer fact.

### Remaining gaps

- **P0 ✔ Closed:** the bridge can consume a genuinely proof-bearing total exactly once and fail closed on mismatch, partial coverage, invalid scope, covered conflict, or opaque lineage.
- **P0 ✔ Closed:** sector estimates cannot enter issuer bridge arithmetic.
- **P1 ✔ Closed:** `not_disclosed` is distinct from `unresolved` and cannot mean zero.
- **P1 ⚠ Source blocker:** zero cached companies currently have a proof-bearing comprehensive securities total. Generic totals, AFS debt totals, and note subtotals remain diagnostic.
- **P1 ⚠ Extraction blocker:** the current corpus contains zero complete-search `not_disclosed` records. Missing fields remain `unresolved` until Arelle/filing evidence proves the searched scope and controlling accession.
- **P1 ⚠ Recovery blocker:** Batch 2A safely classified the problem but did not unlock a new company. Source-proof capture or governed structural promotion is still required before any aggregate recovery.

## Gate decision

Batch 2A's accounting policy and implementation are **verified — user confirmation needed**. The recovery result is honestly limited: one safe numeric control and no new securities unlocks from the cached evidence.

No network retrieval, fresh SEC capture, serving write, threshold change, staging, commit, or Batch 2B finance-lease work occurred.
