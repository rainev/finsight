---
name: structural-schema-preserves-unsupported-forms
description: Structural filing data must preserve well-formed unsupported SEC forms so the eligibility layer can fail closed with an explicit unresolved decision.
metadata: { type: gotcha }
---
`StructuralFiling` is an evidence transport contract, not the filing-eligibility policy. It
must accept a well-formed form such as `8-K` even when that form is ineligible for valuation,
because the structural-shadow consumer represents the evidence and then emits the governed
unsupported-form outcome.

**Why:** Rejecting an unsupported form during deserialization prevents the policy layer from
producing its stable, auditable fail-closed decision and breaks diagnostic replay.

**How to detect / apply:** Validate that `form` is non-empty normalized text in the structural
schema. Apply the `10-K`/`10-Q` eligibility allowlist at acquisition or decision time. Keep a
regression where an 8-K filing survives construction and is classified unresolved by the
shadow-policy consumer.

