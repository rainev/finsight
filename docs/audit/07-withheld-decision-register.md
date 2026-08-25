# Phase 1 withheld-valuation decision register

**Verified:** 2026-08-20 (Asia/Manila)  
**Starting point:** `codex/period-aware-valuation-policy` at `27c2cda`  
**Status:** verified — user confirmation needed; Phase 2 has not started.

## Reference

The approved Phase 1 requires exactly one decision-register row for each of the 83 source-verified withheld companies, keeps the 6 build errors, 4 source failures, and 2 invalid inputs outside that denominator, and requires manual review of every blocker-signature representative, multi-blocker case, remain-withheld proposal, and defensibly estimated accounting impact above 20%.

The real inputs are the byte-equivalent verified replay reports and their regenerated private/public artifacts:

- `output/period-aware-replay-20260819-e/replay-report.json`
- `output/period-aware-replay-20260819-f/replay-report.json`
- `output/period-aware-replay-20260819-e/generated/{TICKER}/valuation-private.json`

## Ours today

Phase 1 produced deterministic, untracked evidence under `output/phase1-withheld-register-20260820/`:

- `register.json` — 83 rows, one per source-verified withheld company.
- `blocker-signatures.json` — 23 complete blocker signatures whose counts sum to 83.
- `exceptions.json` — 6 operating-flow build errors, 4 source-integrity failures, and 2 invalid inputs.
- `challenger-review.json` and `.md` — 42 mandatory reviews covering 23 of 23 signatures and all 37 multi-blocker companies.
- `validation-report.json` and `.md` — denominator, schema, scope, and no-serving-change checks.
- `build_register.py` — cached-artifact-only deterministic generator.

Final register SHA-256: `8ea73deded211634e22aa9706bbcc4d250c90d74339bba7e147e8ea01578a75b`.

## Reuse check and flow

The register reuses the existing period-aware replay and regenerated artifacts; it does not rebuild annual carry-forward, company-history ranges, sector ranges, consolidated forecasting, reliability labels, or the replay runner.

Data flow:

`verified replay -> authoritative private bridge fields -> failure taxonomy -> blocker signatures -> manual challenge -> Sol reconciliation -> final register`

`financials.balance_sheet.bridge_blocking_fields` is authoritative for accounting blockers. `bridge_missing_fields` is retained as context but is not substituted for the blocking set. Model-level failures such as BA's nonpositive primary equity value are recorded separately.

## What backs it

### Verified denominators

- ✔ 106 input candidates = 83 withheld + 11 numeric + 6 build errors + 4 source failures + 2 invalid inputs.
- ✔ 104 valid private artifacts and 94 source-verified rebuilds.
- ✔ The 83 rows have 83 unique tickers and 83 approved dispositions.
- ✔ The 6/4/2 exception lists are disjoint from the 83-row register.
- ✔ The `-e` and `-f` replay JSON reports are equal.
- ✔ Every one of the register's 498 cited evidence paths exists.

### Final failure evidence

Blocking-field occurrences overlap across companies:

- `marketable_securities_noncurrent`: 64
- `finance_lease_total`: 25
- `commercial_paper`: 16
- `marketable_securities_current`: 12
- `cash`: 8
- `preferred_equity`: 4
- `noncurrent_debt`: 4
- `finance_lease_current`: 3
- `finance_lease_noncurrent`: 3
- `noncontrolling_interests`: 1

Final field states across the blocking set:

- `unresolved_extraction`: 77
- `stale`: 39
- `bounded_estimate`: 19
- `conflicting`: 5
- `not_applicable`: 1 model-level entry for BA

No missing information was converted to zero.

### Final dispositions

- ✔ `evidence_repair`: 64 companies.
- ✔ `aggregate_or_range_policy_repair`: 9 — `A`, `ALNY`, `AMGN`, `BDX`, `IDXX`, `ISRG`, `RMD`, `SYK`, `VRT`.
- ✔ `model_lane_review`: 10 — `AMZN`, `BA`, `CL`, `FAST`, `FLEX`, `KVUE`, `PG`, `QSR`, `WBD`, `YUM`.
- ✔ `remain_withheld`: 0 as a terminal Phase 1 disposition. All 83 remain publicly withheld until a later phase actually clears their gates.

The nine aggregate/range cases are the most likely policy unlocks, but that claim remains unverified until Phase 2 proves aggregate coverage, overlap protection, range materiality, and a positive primary valuation.

### Manual review and reconciliation

The Sol-high challenger reviewed 42 mandatory companies: one representative from every signature plus all 37 multi-blocker cases. Its decisions were 28 agree, 12 disagree, and 2 unresolved.

Sol accepted and incorporated:

- BA has a finite but negative FCFF value (`-29.493600094527075` per share; equity value `-23,310,857,296.583366`), so the original “no finite value” wording was false. Percentage impact against negative equity remains economically uninterpretable.
- KO has conflicting cached current candidates and table-context overlap rather than a simple stale/missing condition.
- PM and UPS have finance-lease aggregate/split conflicts; their reported aggregate is not itself a clean resolution.
- Model-lane review is required for the ten companies listed above; bridge repair alone cannot authorize publication.
- Nineteen public replay artifacts collapse detailed private blocker reasons into `BRIDGE_QUALITY_INVALID_OR_MISSING`. The private register remains authoritative, but public/private blocker parity is a later reporting gap.

Sol rejected one early challenger inference:

- The generic “No governed segment forecast evidence” suffix is not proven to be an independent blocker for every bridge-withheld company. `pipeline.py` returns through `_withheld_segment_evidence_result` when the bridge cannot value, and the normal post-bridge path can use consolidated fallback. Post-bridge forecast status remains unverified until replay after bridge repair.

### Materiality

- ✔ Defensibly quantified above-20% accounting-impact cases: 0 of 83.
- ✔ All 83 percentage-impact values remain null because none has a positive, publication-eligible primary equity midpoint.
- ⚠ Plausible but unquantified high-impact risk flags: `APH`, `BA`, `CL`, `CMCSA`, `FLEX`, `KDP`, `KO`, `MO`, `MRVL`, `PM`, `TGT`, `TMUS`, `WBD`, `WMT`, `YUM`.

The risk-flag list is not a threshold result and must not drive promotion.

## Gaps and recommended Phase 2 order

- **P0 ✔ Securities evidence:** resolve the 64 noncurrent and 12 current securities blockers first, including KO's overlapping/context-conflicting cached candidates.
- **P0 ✔ Finance-lease coverage:** next reconcile aggregate versus split coverage for the 25 total-lease blockers; never add an aggregate to either component. Prioritize direct conflicts including PM and UPS.
- **P0 ✔ Residual bridge evidence:** then repair commercial paper, issuer cash, debt, preferred equity, and NCI. Peer cash ranges are not issuer facts.
- **P1 ✔ Model lanes:** keep the ten model-review companies withheld until an issuer-appropriate governed cohort or recovery model exists.
- **P1 ✔ Public/private lineage:** preserve detailed private reasons through the staged public contract after backend policy work is proven.
- **P1 ⚠ Post-bridge forecast status:** replay each repaired company before asserting that consolidated forecasting succeeds or fails.

## Verification evidence and boundaries

- Focused replay tests: `4 passed in 0.18s`.
- Two final register generations produced identical hashes.
- Sol's schema/provenance gate passed for all 83 rows and all 42 mandatory manual reviews.
- Serving-tree hash remained `34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.
- No valuation-policy or serving code changed.
- No network retrieval, fresh SEC capture, paid API, threshold change, staging, or serving promotion occurred.
- Untracked `output/` evidence remains untracked.

Phase 1 is **verified — user confirmation needed**. Phase 2 is intentionally not started.
