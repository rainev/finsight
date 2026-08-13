---
name: xusss-public-normalizer-is-taxonomy-version-bound
description: Do not apply the public 2024 XUSSS/XULE normalization rules to newer SEC taxonomies without a version-matched precision benchmark.
metadata: { type: gotcha }
---
The public XBRL US `2024-ugt-norm.zip` rules can execute successfully against newer SEC filings while silently producing almost no useful normalized facts and making unsafe classifications. In the 2026 FinSight challenge corpus, all ten runs produced valid XBRL-JSON, but none of 51 missing bridge requests was recovered. The same environment produced 237 standardized financial facts across 118 concepts for the official 2024 control filing.

**Why:** The rules are explicitly tied to the 2024 US-GAAP taxonomy. On Kroger's 2026 filing they mapped the combined `LongTermDebtAndFinanceLease` amount to `LongTermDebtNoncurrent` without subtracting leases; on Air Products they emitted a synthetic `OtherAssetsNoncurrent` amount that did not reconcile to either the source account or total assets. A successful process exit is therefore not evidence of safe normalization.

**How to detect / apply:** Before using any XUSSS/XULE rule set, match the rule taxonomy year to the filing taxonomy year, run an intended-version positive control, reconcile every proposed value to its original concept/context, and require zero unsafe promotions. Keep XUSSS as a possible canonical vocabulary and XULE as a rule engine; do not treat the public 2024 mapping bundle as authoritative for 2025/2026 filings. See [[structural-corpus-inputs-are-symlinks]] and `docs/superpowers/handoffs/2026-08-13-xusss-shadow-benchmark.md`.
