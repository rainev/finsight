# FinSight period-aware valuation replay

**Verified:** 2026-08-19 (Asia/Manila)
**Input:** preserved 106-candidate difficult corpus
**Output:** `output/period-aware-replay-20260819-e/` and deterministic rerun `-f/`
**Status:** shadow gate passed; user confirmation required before any serving promotion.

## Verified policy change

- Quarterly/YTD facts define current TTM operating performance.
- Annual balance-sheet snapshots may be carried forward through day 365, with a range based on the larger of a 10% floor or the company’s largest recent annual movement.
- Missing TTM flows are scaled from company-history ratios instead of copying an annual flow into a newer TTM period.
- Missing balance-sheet detail can use company-history ranges and source-verified five-peer archetype/sector ranges.
- Missing segment detail and low classification confidence cap reliability at `Low` instead of automatically deleting an otherwise valid consolidated FCFF valuation.
- A nonpositive supporting EPV is omitted from the public model set; it does not erase a positive primary FCFF valuation.
- Invalid identity, source, period, unit, currency, share denominator, unbounded event, or nonpositive primary value remains fail-closed.

## Replay results

- Input candidates: **106 of 106** immediate candidate directories.
- Valid private artifacts: **104 of 106**; `ADBE` and `SNPS` remained invalid public-shaped inputs.
- Source-verified and rebuilt: **94 of 104** valid private artifacts.
- Source-integrity failures: **4 of 104** — `ALAB`, `COST`, `META`, and `TWLO` had used evidence excerpts that did not match cached filing text.
- Build errors: **6 of 104** — `BIIB`, `ETN`, `JCI`, `SHW`, `TJX`, and `VEEV` lacked enough current or historical operating-flow evidence for the new TTM rule.
- Numeric after: **11 of 94** source-verified rebuilt companies, compared with **0 of 106** legacy public candidates.
- Reliability: **11 Low**, **0 Medium**, **0 High**. No grade was inflated to meet a target.
- Unsafe promotions: **0 of 11** numeric results.
- Public-contract failures: **0 of 94** rebuilt results.
- Serving artifacts changed: **false**; before and after hashes both equal `34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.
- Determinism: the `-e` and `-f` replay reports were byte-equivalent after JSON parsing.

## Newly numeric companies

`ABBV`, `BKNG`, `COHR`, `DXCM`, `EXPE`, `INTU`, `LOW`, `ROK`, `TEVA`, `TMO`, and `VRTX`.

Every one of the 11 was re-read from its regenerated private and public artifacts. Verified for each:

- private primary value equals public base value;
- low ≤ base ≤ high;
- FCFF base equals the private bridge range base within floating-point tolerance;
- every fallback range satisfies low ≤ base ≤ high and retains source accessions; and
- public reliability is `Low`.

## Fallback and threshold evidence

- Current reported fields: **1,046 fields across 94 companies**.
- Annual carried-forward fields: **116 fields across 48 companies**.
- Company-history ranges: **21 fields across 14 companies**.
- Sector estimates: **227 fields across 79 companies**.
- Accounting impact: **5 of 11** at or below 5%, **5 of 11** above 5% through 20%, and **1 of 11** above 20%.
- Scenario movement: **7 of 11** above 20% through 40% and **4 of 11** above 40%.
- No result fell within 0.5 percentage points of a policy boundary, so this replay provides no evidence to change the approved 5%, 20%, or 40% thresholds.

## Remaining limitations

- The six operating-flow build errors still require an archetype-level TTM-flow cohort or additional company history. They are not silently replaced by annual values.
- Most companies still have at least one field with no defensible company or five-peer sector bound.
- Sector estimates are shadow-only evidence from the fixed corpus and have not been promoted into serving data.
- Batch 01 source packets, API receipt, and promotion have not run.

## Test evidence

- Full backend suite: **971 passed, 3 skipped, 1 pre-existing Passlib/Python `crypt` deprecation warning**.
- Replay reports and regenerated artifacts remain under untracked `output/` and must not be staged.
