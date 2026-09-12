# Automated valuation efficiency gap register

Reference: user-approved “Finish FinSight in Small, Verified Working Groups.”
Checked against code and real cached data on 2026-09-09.

## Current flow and reuse

- `build_us_refresh_policies.py` compiles the complete registry and now loads the
  shared concept configuration once. Policy output is unchanged.
- `verify_us_refresh_sources.py` previously rediscovered 1,041 packet directories
  and 981 structural files for every run. One discovery pass took 5.64 seconds
  before any company calculation.
- Source validation receipts span different policy/implementation versions. They
  are useful history but cannot be summed into current release readiness.
- The compilation report had one broad claim-scope reason for most remaining
  operating companies; that label did not distinguish NCI, litigation, acquisition
  payments, commitments or event-state work.

## Gaps and implemented response

| Gap | Severity | Verified delta | Implemented response | Gate |
|---|---|---|---|---|
| EFF-01 | P0 | ✔ No one 440-row status source; “compiled” was repeatedly mistaken for completion | Deterministic work register joins baseline, recipes, compilation and versioned validation receipts | 440 unique rows; separate replay/compiled/current-source/successive states |
| EFF-02 | P1 | ✔ Every cached check rescanned the historical output tree | Immutable content-addressed source index; selected reads rehash bytes and identity | All packet/structural candidates retained; ambiguity never auto-selected |
| EFF-03 | P0 | ✔ Whole checks were serialized and concurrent edits could invalidate results | At most two isolated cached workers run from copied uncommitted code/runtime bytes; deterministic reducer validates coverage and hashes | No acquisition/publication parallelism; missing/duplicate/tampered workers fail |
| EFF-04 | P0 | ✔ Broad claim flag concealed different economics | Hash-verified private claim explanations classify mechanisms; ambiguous cases remain `unclassified_review` | Numeric legacy slot names never prove claim type |
| EFF-05 | P1 | ✔ Progress reporting mixed historical and current-version successes | `refresh_us_valuations.py --work-status` writes concise Markdown plus full machine JSON | Counts are dated/versioned and overlapping blockers are disclosed |

## Real evidence

- Compact source index v3: 1,041 packet directories + 981 structural files =
  2,022 records, 14MB. Cold build 96.83s versus 110MB/111.17s for the
  filing-duplicated draft; every subsequent group avoids recursive discovery.
- Current frozen group `5a2829b8226cfd5449dd4856d1037cd11fbe42e133cd0ca5cf8d33710b528445`
  checks 15 companies with two workers: source-bound AAPL/APO/FITB/SNA and
  11 explicit NCI-group financial reviews. Cold wall time 30.83s; identical
  verified rerun 0.59s with the same report. Worker totals record 0.69s
  preparation, 22.04s source work, 31.44s calculation and 0.003s public checks;
  their 54.27s combined total overlaps in parallel.
- The first NCI-only implementation group added 11 source-grounded mappings and
  preserved their history-derived growth rules. Compilation moved 220 → 231.
  Group `ef35a169e2e20a4b68aa6ae8e19f26c57b9f80067f4b9b64af768696d661e2d7`
  checked all 11; each reached a named bridge-evidence review, so none is called
  a completed update.

## Remaining gaps

- EFF-06 P0 ✔: 188 numeric companies still lack complete update contracts.
- EFF-07 P0 ✔: current register has 4 current-version source-bound companies and
  zero explicit successive-period validations; older successes need rechecking.
- EFF-08 P0 ✔: NCI mapping alone does not solve cash, debt, lease, investment or
  preferred-proof gaps. The 11-company group remains open.
- EFF-09 P1 ✔: a cold full index remains expensive. It is rebuilt only after
  evidence changes; indexed group verification and validated result reuse handle
  routine iteration.

No production catalog, schedule, deployment, paid source or AI runtime changed.
