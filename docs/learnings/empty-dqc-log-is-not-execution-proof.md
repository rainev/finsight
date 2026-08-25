---
name: empty-dqc-log-is-not-execution-proof
description: A zero-message DQC log proves nothing unless Xule rule execution is recorded.
metadata: { type: gotcha }
---
An empty DQC diagnostic list can mean clean data, no applicable rules, a missing log, or a plugin that never ran.

**Why:** The initial DQC artifacts returned `pass` with zero messages but carried no rule-execution evidence.

**How to detect / apply:** Require zero subprocess errors, a present log, exact ruleset/taxonomy hashes, and canonical Xule rule statistics with `DQC.US.*` names. Report zero applicable assertions as `pass_no_applicable_rules`, not an unqualified pass. DQC remains diagnostic-only and can never create a value.
