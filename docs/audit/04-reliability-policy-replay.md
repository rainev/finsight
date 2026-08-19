# FinSight reliability-policy replay

**Run date:** 2026-08-19 (Asia/Manila)
**Input:** `/Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery`
**Output:** `output/reliability-pipeline-replay-20260819b/`
**Status:** verified replay evidence; phase gate remains open because no source-verified candidate produced a numeric public value.

## Verified results

- **106 of 106** immediate candidate directories were counted. The denominator excludes only the `sec-cache` directory; cache contents did not define the denominator.
- **104 of 106** candidates contained valid private valuation artifacts. `ADBE` and `SNPS` were rejected as public-shaped/incomplete inputs.
- **100 of 104** valid private artifacts passed source verification. `ALAB`, `COST`, `META`, and `TWLO` failed because their used filing-evidence excerpts were not found in the matching cached filing HTML.
- **0 of 100** source-verified candidates produced a finite public base value after regeneration. All 100 were withheld by current bridge or publication blockers.
- **0 of 100** source-verified candidates were counted as unsafe promotions.
- **0 of 100** source-verified candidates received a High, Medium, or Low reliability count because reliability buckets apply only to finite numeric-after results.
- Accepted field fallback usage across the 100 source-verified candidates was **1,277 current-reported fields** and **123 annual-carried-forward fields**. The annual carry-forward path was used by **51 of 100** companies; the current-reported path was present in **100 of 100**.
- Accounting-impact and scenario-movement buckets contain **0 cases** because no candidate reached a finite public result. This means the replay did not yet test whether finite uncertainty is graded fairly; it did not prove the thresholds fair.
- Serving artifacts were unchanged: the before/after combined serving hash was identical.
- The bridge-policy baseline exited with the expected evidence-gate status `2`, wrote diagnostics, and did not change serving artifacts.
- The reliability replay was deterministic: two independent output directories produced byte-identical `replay-report.json` summaries.
- The current replay-generated public directory served **100 of 100** withheld artifacts through the FastAPI `TestClient`; list and detail both returned HTTP 200, the detail reliability label was `Low`, and prohibited private keys were absent.
- A real TCP listener could not be started in this sandbox: binding `127.0.0.1:8765` returned `operation not permitted`. The in-process HTTP consumer check is verified; external `curl` verification remains unverified until run in an environment that permits local binding.
- The FastAPI serving import path contains no Arelle import; Arelle remains isolated to offline structural-ingestion modules.

## Main observed blockers

The regenerated candidates were generally withheld because the enterprise-to-equity bridge still lacked current evidence for one or more material items—especially marketable securities, noncontrolling interests, preferred equity, commercial paper, and finance leases. Many also had no governed segment forecast evidence for the normalized period.

This is a real data/evidence limitation, not a reason to substitute zero, silently switch models, or promote an Arelle shadow result. The replay therefore confirms the fail-closed behavior but does not yet demonstrate the intended finite Low-reliability fallback behavior.

## Interpretation

- **Verified improvement:** the new runner can replay the real cached corpus offline, validate source integrity, preserve the full denominator, count annual carry-forward usage, prevent serving writes, and distinguish legitimate withholding from unsafe promotion.
- **Verified limitation:** the available corpus does not contain enough accepted current bridge evidence to produce numeric results under the current governed model routes.
- **Unverified:** whether the 5%, 20%, and 40% reliability thresholds are fair for finite results. No threshold change is justified by this replay.
- **Unverified:** whether Batch 01 can pass. The ten-company batch must not start until the Phase 1 API and reliability gates are satisfied or the evidence gap is explicitly resolved.

## Verification commands

```bash
PYTHONPATH=backend pytest -q backend/tests/test_reliability_pipeline_replay.py
PYTHONPATH=backend pytest -q backend/tests

python3 scripts/run_bridge_policy_shadow.py \
  --input-root '/Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery' \
  --output-dir output/bridge-policy-replay-20260819

python3 scripts/run_reliability_pipeline_replay.py \
  --input-root '/Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery' \
  --output-dir output/reliability-pipeline-replay-20260819b
```

Test evidence: `959 passed, 3 skipped, 1 pre-existing Passlib/Python crypt deprecation warning`. Replay evidence is in the untracked output directory and must not be staged.
