# Audit 21 — free official specialist sources

Reference: `/Users/carlosconda/Downloads/PLAN.md` Phase 3, lines 76–125.

## Ours today

✔ `specialist_model_adapters.py` contains useful input-explicit bank, sum-of-parts, and REIT mechanical transformations, and explicitly refuses issuer defaults or invented missing values (`lines 1-7`, `126-297`).

✔ Current bank/utility/REIT dispatch remains Companyfacts-based (`equity_models.py:51-90`, `353-464`). Generic extractors filter period ends rather than all filing dates (`93-121`), then only some fields are overwritten by strict cutoff-selected facts (`376-389`, `420-452`), leaving a look-ahead risk for optional/non-overridden inputs.

✔ No FR Y-9C, FFIEC Call Report, FERC, RSSD/LEI crosswalk, regulatory packet, or SEC Exhibit 99 supplement ingestion exists under `backend/app/us_valuation`, `scripts`, or the specialist tests. Existing adapters are arithmetic only.

✔ Issuer classification uses SEC CIK/SIC and recent SEC accessions (`classification.py:83-115`); it cannot prove parent-regulated-entity relationships or consolidation/allocation bridges.

## Reuse check

Reuse the official-evidence request/candidate/decision records from Phases 1–2, immutable packet cache, source hashing, and specialist mechanical adapters. Each regulator needs a small parser at the pipeline boundary, not a new valuation framework.

## Consumer flow and backing

The required flow is issuer identity → official regulator/SEC supplemental packet → parent/subsidiary bridge → governed evidence decisions → existing specialist adapter. Current flow jumps from Companyfacts directly to the adapter and therefore cannot exhaust applicable official specialist sources.

## Gaps

- **P0 ✔ OE3-01:** Add versioned specialist packet/receipt contracts with source URL, retrieval/cutoff dates, immutable payload hashes, period, units, entity identifiers, and explicit unsupported/failure outcomes.
- **P0 ✔ OE3-02:** Build a verified CIK–RSSD–LEI crosswalk and parent/subsidiary/consolidation bridge; reject regulator facts without exact identity and scope proof.
- **P0 ✔ OE3-03:** Add parent-level FR Y-9C ingestion for common/preferred equity, CET1/total capital, RWA, ratios/buffers, and credit-quality inputs; use FFIEC Call Reports only as subsidiary corroboration.
- **P0 ✔ OE3-04:** Add FERC Form 1/Form 3-Q ingestion for regulated identity, rate base/allowed return when reported, capital structure/debt, operations, and ownership/allocation evidence; never project operating-utility facts directly to the public parent.
- **P0 ✔ OE3-05:** Extend SEC attachment capture to filed 8-K Exhibit 99 supplements and preserve issuer-defined FFO/AFFO reconciliations, NOI/occupancy, recurring adjustments, claims, and diluted shares without standardizing AFFO.
- **P0 ✔ OE3-06:** Remove specialist look-ahead by requiring every consumed input—not only strict overrides—to carry `filed <= valuation_date` provenance.
- **P0 ✔ OE3-07:** Add real/representative packet fixtures and acceptance cases for JPM/BAC, NEE, and Realty Income that either reconcile exact official inputs or emit a precise unsupported-source decision.

Status: audit complete; all findings were rechecked firsthand in the cited files. No pipeline code changed in this batch.
