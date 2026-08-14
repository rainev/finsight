# Audit 01 — Publication strictness

Status: **firsthand verified — incorporated into the approved design**

## Reference

The agreed product target is:

- one numeric intrinsic-value estimate for every company in a fixed 500-company universe;
- one consistent public experience, including intrinsic value and undervalued/overvalued percentage;
- one user-facing reliability label: `High`, `Medium`, or `Low`;
- uncertainty should normally lower reliability and widen the valuation range instead of removing the number.

## Ours today

The evidence-policy implementation exists on `feat/evidence-aware-bridge-policy`, not yet on this clean whole-universe branch.

1. Only `reported`, `explicit_zero`, and `evidence_backed_zero` are accepted as ordinary point values. A claim may additionally be `not_applicable` (`backend/app/us_valuation/bridge_policy.py:22-26`).
2. A record is rejected when its authority is not `production`, its freshness is not exactly `current`, or its source metadata is incomplete (`bridge_policy.py:577-602`).
3. Every unusable required field becomes a blocker (`bridge_policy.py:605-624`).
4. One blocker makes `can_value` false (`bridge_policy.py:945-960`).
5. Materiality is not calculated when any blocker exists: the assessment immediately returns `withheld` without an intrinsic-value range (`bridge_policy.py:964-990`).
6. Bounded uncertainty is supported, but the global spread ceiling is only 1% (`bridge_policy.py:13-15`).
7. The structural shadow gate fails the entire company when any requested field is not accepted (`backend/app/us_valuation/structural_shadow.py:172-237`).

## Reuse check

The existing design already provides most of the machinery needed for a less rigid policy:

- `FieldAvailability` states preserve why a value is reported, stale, unresolved, estimated, or bounded.
- `BridgeRange` carries low, midpoint, and high values.
- `assess_bridge_materiality()` measures how accounting uncertainty changes per-share intrinsic value.
- Arelle extracts the full filing structure offline, while serving reads normalized artifacts.

The policy should extend these parts rather than create a second valuation pipeline.

## Current flow

```text
SEC filing → Arelle/Companyfacts → normalized field
           → any unresolved required field?
               yes → withhold before measuring its valuation impact
               no  → calculate valuation and materiality
```

This order is the central strictness problem. FinSight often refuses to calculate how important a missing item is because the item is already classified as a blocker.

## What backs this audit

The 104-company cached replay parsed 104/104 filings with zero parser failures. It evaluated 545 field requests: 2 accepted in shadow, 42 review, 353 rejected, and 148 unresolved. All 104 cases were withheld and no public artifact changed (`docs/audit/02-evidence-aware-bridge-replay.md:95-117` on the evidence-policy branch).

The bridge replay found 104 valid private artifacts and 2 invalid public-shaped inputs. It produced 0 complete, 0 bounded, and 106 withheld decisions. The valid companies had at least one blocker each; 103 of 104 had at least two. Frequent blockers were finance-lease current (91), finance-lease noncurrent (88), noncurrent securities (79), current securities (66), and preferred equity (61) (`docs/audit/02-evidence-aware-bridge-replay.md:131-160`).

## Gaps

1. **P0 ✔ Materiality is checked too late.** Any unresolved field causes withholding before FinSight measures whether that field changes intrinsic value by one cent or fifty dollars.
2. **P0 ✔ The current gate cannot meet 500/500 numeric coverage.** At least one blocker means no usable valuation, while all 104 tested difficult cases had at least one blocker.
3. **P0 ✔ The current release contract conflicts with the latest product decision.** The root-only whole-universe plan targets at least 450 numeric values and makes low scores unavailable; the user has now made 500/500 numeric coverage the target.
4. **P1 ✔ Freshness is binary.** A source-linked annual value becomes fully unusable when it is not from the current period, even when carrying it forward with a reliability penalty may be reasonable.
5. **P1 ✔ Bounded uncertainty exists in code but has no real-data creation path in the replayed corpus.** The corpus contained zero bounded fields, so the safer lower-reliability path was never reachable.
6. **P1 ✔ Structural evidence cannot improve production today.** Every Arelle candidate in the replay had `shadow` authority and therefore could not become a valuation input. A governed promotion step is still required.
7. **P1 ✔ Reliability is not the main decision mechanism.** The current policy first decides publish/withhold; it does not assign `High`, `Medium`, or `Low` based on the actual effect of accounting uncertainty.
8. **P1 ⚠ Universe-wide effect is not yet known.** The findings are verified for the 104-company difficult-case corpus, not for a canonical 500-company universe. The 500-company manifest and full replay remain to be built.

## Batch conclusion

The parser is not the main cause of zero publication in this batch. The main cause is policy order: FinSight treats unresolved details as automatic blockers before calculating whether they materially change the valuation. The next design should preserve source evidence and conflict checks, but move uncertainty measurement before the final reliability decision.
