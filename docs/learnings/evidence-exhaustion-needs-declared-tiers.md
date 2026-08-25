---
name: evidence-exhaustion-needs-declared-tiers
description: One failed source attempt is not proof that all applicable evidence tiers were exhausted.
metadata: { type: gotcha }
---
An evidence receipt cannot infer exhaustion from `attempts.length > 0`. Each material request must declare its applicable tiers and carry a terminal value, blocker, failure, or no-candidate outcome for every one.

**Why:** The first FOD4 receipt marked unresolved requests exhausted after only the structural attempt and attached generic specialist blockers to unrelated fields.

**How to detect / apply:** Declare applicable sources per field/model, distinguish Companyfacts, structural XBRL, tables, regulator/supplement, aggregate, annual, company-history, and sector tiers, and synthesize explicit no-candidate attempts for searched empty tiers. Add specialist attempts only to fields that source can address and run the model-route guard. Preserve source class, filed lineage, identity, unit, scope, and coverage through projection.
