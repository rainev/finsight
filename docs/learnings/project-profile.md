---
name: project-profile
description: Defines the real thing, verification method, and evidence required for FinSight pipeline work.
metadata: { type: project }
---
FinSight is a composable data-pipeline project: build/runtime follows the `development` profile, while correctness verification and evidence follow the `analysis` profile. The real thing is the source-linked SEC or regulator package flowing through normalization and the correct valuation lane into generated public-safe JSON and the staged FastAPI list/detail endpoints. Verify by replaying cached real inputs, reconciling identities, cutoffs, periods, units, candidate decisions, arithmetic, hashes, and representative issuer traces, then calling the real local API. Evidence is the replay validation output, deterministic diffs/hashes, exact denominators, source-linked traces, and API responses; UI evidence is additionally required when UI behavior changes. See `.codex/goodbehavior/profiles/finsight-us-valuation.md`.
