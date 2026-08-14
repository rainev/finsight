# Evidence foundation integration audit

Verified: This audit covers Task 1 of the evidence-aware reliability pipeline on `feat/whole-universe-greenlight`.

## Inputs and merge

Verified: The target branch was `feat/whole-universe-greenlight` at base SHA `0997f627297b64d3cc7340865e253a7951e52068`.

Verified: The source branch `feat/evidence-aware-bridge-policy` resolved to SHA `e1cd1e25983c888021812868f53bd2444f6c9f8e`.

Verified: The required source branch was merged with `git merge --no-commit --no-ff feat/evidence-aware-bridge-policy`; the merge stopped with exit 1 because Git found documentation conflicts.

Verified: The merge conflicts were `docs/learnings/INDEX.md`, `docs/plans/ROADMAP.md`, and `docs/plans/PRODUCTION-BACKLOG.md`; no implementation file conflicted.

Verified: The `docs/learnings/INDEX.md` resolution retains the whole-universe threshold pointer and all evidence-branch learning pointers, with no conflict markers.

Verified: The roadmap and production-backlog conflicts were resolved additively, preserving the target branch's whole-universe plan and the source branch's evidence-policy notes.

Unverified: The brief predicted that only `docs/learnings/INDEX.md` would conflict; the additional two documentation conflicts were not predicted by that expectation.

## Focused foundation suite

Verified: The exact focused command was:

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_field_availability.py \
  backend/tests/test_field_availability_normalizer.py \
  backend/tests/test_bridge_policy.py \
  backend/tests/test_bridge_policy_pipeline.py \
  backend/tests/test_structural_xbrl_schema.py \
  backend/tests/test_structural_xbrl_integration.py \
  backend/tests/test_structural_shadow.py
```

Verified: The focused suite exited 0 with `284 passed in 1.47s`.

## Full backend suite

Verified: The exact full-suite command was `PYTHONPATH=backend pytest -q backend/tests`.

Verified: The full suite exited 0 with `811 passed, 3 skipped, 1 warning in 8.76s`.

Verified: The warning was the existing Python 3.11 `crypt` deprecation warning emitted through `passlib`; it did not fail a test.

Verified: The full-suite result matches the expected baseline of `811 passed, 3 skipped`.

## Immutable replay

Verified: The replay output directory was absent before execution: `output/bridge-policy-integration-baseline`.

Verified: The exact replay command was:

```bash
python3 scripts/run_bridge_policy_shadow.py \
  --input-root /Users/carlosconda/Desktop/Investing\ Application/output/legacy-fcff-bridge-recovery \
  --output-dir output/bridge-policy-integration-baseline
```

Verified: The replay exited 2 and printed `evidence gate failed; diagnostics written` followed by `wrote bridge-policy-shadow.json and bridge-policy-shadow.md to /Users/carlosconda/Desktop/Investing Application/.worktrees/whole-universe-greenlight/output/bridge-policy-integration-baseline`.

Verified: Exit 2 represents the known zero-publication evidence gate, not a process or parsing failure; the command produced both replay artifacts.

Verified: The replay input denominator was 106 artifact candidates: 104 valid private company artifacts and 2 invalid/error public-shaped artifacts.

Verified: The replay decision counts were `bounded_candidate=0`, `complete=0`, and `withheld=106`.

Verified: The replay field-state counts were `evidence_backed_zero=7`, `explicit_zero=34`, `proxy=4`, `reported=716`, `stale=265`, and `unresolved=430`.

Verified: The replay reason-code counts were `NOT_PRIVATE_VALUATION_ARTIFACT=2`, `STALE_STALE_REPORTED_FACT=89`, and `UNRESOLVED_UNSPECIFIED=102`.

Verified: The replay reported `serving_artifacts_changed=0`, no missing tickers, and no duplicate tickers.

Verified: The replay JSON recorded `evidence_gate_passed=false`; this is the expected baseline evidence result and is not described as a passing publication gate.

Unverified: No API list/detail request or browser flow was run because Task 1's required gates are the foundation tests and immutable bridge-policy replay; API/UI verification remains a later roadmap gate.

## Output and serving-data integrity

Verified: Generated evidence exists only at `output/bridge-policy-integration-baseline/bridge-policy-shadow.json` and `output/bridge-policy-integration-baseline/bridge-policy-shadow.md` and remains untracked.

Verified: `git diff --name-only -- backend/app/data/us_valuations frontend/public/data` returned no paths after replay.

Verified: The staged merge passed `git diff --cached --check` before this audit was added.

## Gate conclusion

Verified: The evidence-aware foundation is present in the staged merge, including `FieldAvailability`, `BridgeResolution`, structural-XBRL/Arelle support, pipeline integration, public-sanitizer protections, and its tests.

Verified: The focused suite, full backend baseline, and reproducible offline replay completed with the exact results recorded above.

Unverified: Final commit SHA and post-commit `0997f62..HEAD` self-review are recorded in the task report after commit execution.
