# Audit 23 — replay, measurement, and rollout gate

Reference: `/Users/carlosconda/Downloads/PLAN.md` Phase 5, lines 150–202.

## Ours today

✔ Deterministic, serving-safe replay machinery exists. `scripts/run_reliability_pipeline_replay.py:23-160` forbids serving-root output and hashes protected roots; later validation checks source manifests, private/public contracts, evidence lineage, and unsafe promotion. Batch-specific capture/runners also enforce immutability and serving sentinels.

✔ Local artifacts preserve Batch 01/02 results, a 104-company supported structural corpus, and a cumulative seven-company withheld register (`docs/plans/EVIDENCE.md`; `docs/audit/14-universe-reset-withheld-register.md`). The requested plan calls it 106-company difficult corpus, so the exact current denominator/source manifest must be reconciled rather than assumed.

✔ Existing historical evidence reports byte equality, full backend suites, localhost FastAPI parity, private-field protection, and no serving writes, but it predates the unified evidence schema and specialist sources.

✔ There is no single replay command/report covering Batch 01, Batch 02, difficult corpus, and cumulative withheld register with the plan's material-request, rescue-source, custom-tag, restatement, DQC, before/after valuation, true-cause, unsafe-promotion, deterministic-hash, and serving-change metrics.

## Reuse check

Extend the existing protected-root hash helpers, replay source validation, batch manifests, structural corpus receipts, sanitizer/API checks, and withheld-register loader. Do not mutate the frozen source packets or serving directories.

## Consumer flow and backing

The real verification output is a reproducible report generated twice from frozen cached inputs, reconciled to exact issuer/request denominators and representative source/arithmetic traces, followed by the real staged localhost API. A successful script exit or historical test count is not sufficient.

## Gaps

- **P0 ✔ OE5-01:** Build one replay manifest that deduplicates and identifies Batch 01, Batch 02, the exact difficult corpus, and cumulative-withheld issuers; reconcile the plan's 106 denominator against locally available 104 supported cases plus exclusions.
- **P0 ✔ OE5-02:** Emit every requested metric and an explicit evidence outcome for every material request, including package/parser failures and applicable-source exhaustion.
- **P0 ✔ OE5-03:** Compare before/after numeric and withheld outcomes by true cause; require zero unsafe promotions and preserve unsuitable-model/nonpositive/event/conflict withholds.
- **P0 ✔ OE5-04:** Regenerate twice and prove byte identity plus unchanged protected serving hashes; keep all outputs under untracked `output/`.
- **P0 ✔ OE5-05:** Run focused and complete backend suites, then serve the staged output through real localhost FastAPI and prove list/detail parity, unchanged public shape, no private evidence, and no Arelle/regulator parser imports.
- **P0 ✔ OE5-06:** Freeze Batch 03, promotion, merge, push, and deploy until the complete replay evidence is presented and user-confirmed.

Status: audit complete; all findings were rechecked firsthand in the cited files. No pipeline code changed in this batch.
