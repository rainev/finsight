# Evidence-aware bridge policy replay

Status: **verified — user confirmation needed**

## Decision

Task 8 replay tooling is verified on the current private corpus. Structural
candidates remain shadow-only, legacy availability is reconstructed from its
source records, every evaluated private case remains withheld, and no serving
artifact changed.

Bounded-review activation is **withheld pending evidence**. The corpus contains
zero real bounded candidates, two non-private payloads, and only five of the ten
requested representative private artifacts. This audit does not authorize BP4
or promote any valuation.

## Basis and boundaries

- Starting feature commit: `4332d6139e9c4d3f60d98ee98cb7998a64e8efb0`.
- Primary input root:
  `/Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery`.
- Full Task 8 output: `output/bridge-policy-shadow/` (untracked).
- Representative output: `output/bridge-policy-shadow-representative/`
  (untracked).
- Fresh Task 6 structural output:
  `output/structural-xbrl-full-corpus/results-task6-replay-20260813/`
  (untracked and controller-owned).
- The replay used local artifacts and cached structural filing packages. It made
  no network call, imported no Arelle code in the bridge-policy CLI, and wrote
  no backend or frontend serving artifact.

## TDD evidence

All production behavior was introduced after an observed failing test.

| Gate | Command | Observed RED | Observed GREEN |
| --- | --- | --- | --- |
| Pure evaluator | `pytest -q backend/tests/test_bridge_policy_shadow.py` | collection error: `ModuleNotFoundError: app.us_valuation.bridge_policy_shadow`; `1 error` | `6 passed in 0.03s` |
| Corpus evaluation | same focused file | collection error: `cannot import name 'evaluate_corpus'`; `1 error` | `14 passed in 0.04s` |
| Explicit structural diagnostics | `pytest -q backend/tests/test_bridge_policy_shadow.py::test_structural_candidate_presence_requires_explicit_shadow_diagnostics` | expected `True`, observed `False`; `1 failed` | full file reached `15 passed in 0.04s` |
| Bounded CLI | `pytest -q backend/tests/test_bridge_policy_shadow.py -k cli` | script absent; `5 failed, 15 deselected` | `5 passed, 15 deselected in 0.42s` |
| Exact modern serialization | `pytest -q backend/tests/test_bridge_policy_shadow.py -k canonical_serialization` | extra keys were normalized instead of rejected; `3 failed` | full file `23 passed in 0.44s` |
| Independent-review hardening | `pytest -q backend/tests/test_bridge_policy_shadow.py -k 'precheck_mismatch_precedes or dangling_candidate or normal_cli_run or output_pair or case_variant'` | `5 failed, 1 passed, 23 deselected` | `6 passed, 23 deselected in 0.12s` |

The tests exercise real functions and subprocess CLI behavior. They cover legacy
and modern artifacts, bounded and blocked cases, stored-precheck mismatch,
malformed/non-object/non-private inputs, duplicates, requested and missing
tickers, dangling candidates, input immutability, sorted output,
filesystem-identity path rejection, same-directory no-clobber pair publication,
byte-identical reruns, immutable-output refusal, and a normal CLI run with
explicit Arelle-import and network blockers.

## Automated verification

Baseline before Task 8:

```text
pytest -q backend
782 passed, 3 skipped, 1 warning in 8.03s
```

CLI help:

```text
python3 scripts/run_bridge_policy_shadow.py --help
exit 0; --input-root, --output-dir, and --tickers present
```

Task 8 evaluator and CLI:

```text
pytest -q backend/tests/test_bridge_policy_shadow.py
29 passed in 0.50s
```

Focused Task 1–8 and structural suite:

```text
pytest -q backend/tests/test_structural_xbrl_schema.py backend/tests/test_concept_resolver.py backend/tests/test_arelle_adapter.py backend/tests/test_filing_package.py backend/tests/test_structural_shadow.py backend/tests/test_field_availability.py backend/tests/test_field_availability_normalizer.py backend/tests/test_bridge_policy.py backend/tests/test_bridge_policy_pipeline.py backend/tests/test_bridge_policy_artifacts.py backend/tests/test_bridge_policy_shadow.py
656 passed in 6.83s
```

Authoritative full backend suite:

```text
pytest -q backend
811 passed, 3 skipped, 1 warning in 8.33s
```

The only warning is the pre-existing Passlib use of Python's deprecated `crypt`
module.

## BP1 — fresh structural shadow replay

Command:

```text
python3 scripts/run_structural_xbrl_shadow.py --data-root output/structural-xbrl-full-corpus/input --cache-dir output/structural-xbrl-pilot/cache --output-root output/structural-xbrl-full-corpus/results-task6-replay-20260813
```

Observed exit: `0`.

| Metric | Result |
| --- | ---: |
| Discovered / eligible / parsed | 104 / 104 / 104 |
| Parser failed / skipped | 0 / 0 |
| Accepted shadow / review / rejected / unresolved | 2 / 42 / 353 / 148 |
| Publish / lower-confidence candidates | 0 / 0 |
| Withheld cases | 104 |
| Reports / decisions / serialized availability candidates | 104 / 545 / 545 |
| Missing availability candidates | 0 |

Every candidate had authority `shadow`; all 104 reports retained
`publication_effect: none_shadow_only`. Controller before/after aggregate hashes
were unchanged: 106 primary inputs
`e76f54df5817b9863a1534197b3d0021bd513eca` and 218 public serving JSONs
`76d3e4e72294209b052328f4d0fb9ecef21314e2`.

## BP3 — complete private corpus replay

Command:

```text
python3 scripts/run_bridge_policy_shadow.py --input-root '/Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery' --output-dir output/bridge-policy-shadow
```

Observed exit: `2`, after both diagnostics were written. This is the expected
evidence-gate result because ADBE and SNPS are public/non-private payloads; it is
not a tooling failure.

| Metric | Result |
| --- | ---: |
| Candidate artifacts | 106 |
| Valid private / invalid non-private | 104 / 2 |
| Complete / bounded candidate / withheld | 0 / 0 / 106 |
| Serving artifacts changed | 0 |
| Missing requested / duplicate tickers | 0 / 0 |
| Eligibility changes versus legacy | 0 |

Invalid cases were counted, not skipped:

- ADBE — `NOT_PRIVATE_VALUATION_ARTIFACT`.
- SNPS — `NOT_PRIVATE_VALUATION_ARTIFACT`.

Blocker frequencies:

| Field | Count | Field | Count |
| --- | ---: | --- | ---: |
| cash | 9 | commercial paper | 53 |
| current debt | 27 | noncurrent debt | 27 |
| finance lease current | 91 | finance lease noncurrent | 88 |
| finance lease total | 54 | current securities | 66 |
| noncurrent securities | 79 | preferred equity | 61 |
| noncontrolling interests | 53 |  |  |

Field states were `reported=716`, `unresolved=430`, `stale=265`,
`explicit_zero=34`, `evidence_backed_zero=7`, and `proxy=4`. There were no
bounded fields. The 104 valid private artifacts were all legacy artifacts, so
the evaluator reconstructed availability from `values`, `sources`, and
`field_states`; it did not synthesize `total_interest_bearing_debt` evidence.

## Representative replay and source lineage

Command:

```text
python3 scripts/run_bridge_policy_shadow.py --input-root '/Users/carlosconda/Desktop/Investing Application/output/legacy-fcff-bridge-recovery' --output-dir output/bridge-policy-shadow-representative --tickers AMZN,CAT,RCL,PEP,WMT,AAPL,MSFT,ANET,CRM,WDC
```

Observed exit: `2`, after diagnostics were written. Five requested private
artifacts were unavailable. Matched: AMZN, CAT, PEP, RCL, WMT. Missing: AAPL,
ANET, CRM, MSFT, WDC. All five evaluated artifacts were valid and withheld;
none was complete or bounded.

| Ticker | Controlling period / accession | Firsthand lineage result | Outcome |
| --- | --- | --- | --- |
| AMZN | `2026-06-30` / `0001018724-26-000026` | **PASS.** Every non-null bridge source matches. Commercial paper is a governed explicit zero from the same period/accession. Noncurrent securities and NCI remain unresolved; no absent field became zero. | Withheld |
| CAT | `2026-03-31` / `0000018230-26-000021` | **PASS.** Current sources reconcile. Current securities remain explicitly stale from accession `0000018230-14-000386`; current and noncurrent debt remain stale from `0000018230-26-000008` (2025-12-31 evidence). These are expected blockers, not reconciliation failures. | Withheld |
| RCL | `2026-03-31` / `0000884887-26-000026` | **PASS.** Current sources reconcile. Commercial paper remains stale from `0000884887-22-000008`; lease split and total evidence remain stale from `0000884887-26-000007` (2025-12-31). | Withheld |
| PEP | `2026-06-13` / `0000077476-26-000035` | **PASS.** Current non-null sources reconcile. Preferred equity remains stale from `0000077476-19-000017` (2018 evidence); absent lease and noncurrent-securities fields remain unresolved. | Withheld |
| WMT | `2026-04-30` / `0000104169-26-000102` | **PASS.** Current lease components reconcile and are counted once. Commercial paper remains stale from `0001193125-09-248603`, lease total from `0000104169-26-000055` (2026-01-31), and preferred equity from `0001193125-10-071652`. The stale total is not added to the current split. | Withheld |

The stale period/accession differences are the evidence for withholding. They
were not treated as current and were not silently coerced to zero.

## Determinism and nonmutation

Both Task 8 commands were rerun unchanged and again exited `2`. Output bytes
were identical:

| Output | SHA-1 before and after rerun |
| --- | --- |
| Full JSON | `f15ec8f1bc5e514e1675f5ac2dee8d2b98638e67` |
| Full Markdown | `5dd2dd7c93e291edaf1b7b128d4a1dd106a16920` |
| Representative JSON | `0e78a8f2b4881f10b53108346cf98a81e4d9ee79` |
| Representative Markdown | `0319bcf1382e8895a025a13f5ba908cc35319de3` |

An independent concatenated-byte SHA-1 check was unchanged before/after Task 8:

- 106 private inputs: `587751960ca1bf0c0f4d57b640c3cb4a2c24101c`.
- 218 backend/frontend serving JSONs:
  `b93d712e0b043d9e275dea697d90015aa8dce571`.

Each output directory contains only `bridge-policy-shadow.json` and
`bridge-policy-shadow.md`; no staging or lock file remained. Tests also proved
that a differing existing output fails before either immutable file is
overwritten, concurrent publication cannot clobber a target, and a second-file
publication failure rolls back the first file.

An abrupt process termination may leave `.bridge-policy-shadow.lock`. This is a
fail-safe refusal, not an overwrite risk; an operator must verify no writer is
active before removing it. Automated stale-lock recovery is backlogged as B11.

## Publication and activation gate

- Structural publication effects: 104/104 `none_shadow_only`.
- Private bridge eligibility deltas: 0.
- Valid private decisions: 104/104 withheld.
- Invalid/non-private decisions: 2/2 deterministic withheld/error cases.
- Public serving artifacts changed: 0.
- Real bounded candidates: 0.

Therefore BP1, BP2, and BP3 are firsthand-verified. BP4 remains **withheld
pending evidence** until current source-linked private artifacts exist, every
required accession reconciles, a real joint intrinsic-value spread is at most
1%, and public artifacts remain unchanged.
