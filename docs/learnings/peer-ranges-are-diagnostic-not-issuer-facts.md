---
name: peer-ranges-are-diagnostic-not-issuer-facts
description: Sector or peer ranges may inform review but must not enter an issuer's enterprise-to-equity bridge as accounting evidence.
metadata: { type: gotcha }
---
A five-peer or sector percentile range is not a fact about the issuer. Preserve it as diagnostic evidence, but reject `fallback_level="sector_estimate"` from bridge arithmetic even when it has finite bounds, accessions, and production-looking metadata.

**Why:** In the period-aware replay, peer midpoints entered cash-and-investments and allowed ten companies to produce numeric shadow values. A bounded label did not make those values issuer-specific.

**How to detect / apply:** The bridge returns `BRIDGE_EVIDENCE_NOT_ISSUER_SPECIFIC` for a sector estimate. The fallback decision remains visible for research, while the issuer field stays blocking until current filing evidence, a source-linked company-history range, or a proven aggregate exists.
