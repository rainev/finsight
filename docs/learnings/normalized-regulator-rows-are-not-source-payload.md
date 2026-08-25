---
name: normalized-regulator-rows-are-not-source-payload
description: A hash of parsed regulator rows cannot substitute for the official downloaded packet hash.
metadata: { type: gotcha }
---
A deterministic JSON hash over normalized FR Y-9C, Call Report, or FERC rows proves only the caller-provided normalization. It does not prove the official payload, source version, entity, or record codes.

**Why:** The public FFIEC/NIC Q2 bulk endpoint returned HTTP 403, so the parser could still create a neat normalized packet without ever receiving the source bytes.

**How to detect / apply:** Store separate official-payload and normalized-row hashes, exact dataset/version/record IDs, parser version, and source URL. A packet without the official payload hash is non-promotable. Preserve HTTP/cache/discovery failures explicitly instead of filling the fact list.
