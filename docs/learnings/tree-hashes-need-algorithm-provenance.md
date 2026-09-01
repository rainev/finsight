---
name: tree-hashes-need-algorithm-provenance
description: Compare protected-root hashes only when the producing scripts use the same tree-hash algorithm.
metadata: { type: gotcha }
---
The SEC capture guard and history runner can report different SHA-256 strings for the same
unchanged serving tree because one hashes raw file bytes while another hashes each file digest
into the tree ledger.

**Why:** comparing those values across scripts creates a false mutation alarm even when every
script's own before/after values match and Git reports no change.

**How to detect / apply:** treat each guard's before/after pair as the mutation proof. Before
comparing hashes produced by different commands, inspect the hash function or recompute both
trees with one canonical helper; corroborate with scoped `git status` and `git diff`.
