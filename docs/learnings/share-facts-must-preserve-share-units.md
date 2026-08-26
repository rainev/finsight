---
name: share-facts-must-preserve-share-units
description: A numerically correct share denominator is still invalid provenance when a generic point helper labels it USD.
metadata: { type: gotcha }
---
Load-bearing share facts must retain their actual XBRL share unit (`xbrli:shares` or the normalized equivalent). A generic balance-sheet point helper that hardcodes USD may reproduce the right number while creating false private provenance.

**Why:** Unit identity is part of the source-safety gate. A correct value with the wrong unit can hide a later scaling or concept-selection error.

**How to detect / apply:** Assert the structural row's concept, period, value, and share unit together. Use a unit-aware instant-fact helper for current shares and keep USD-only helpers limited to monetary facts. See also [[specialist-facts-require-filed-lineage]].
