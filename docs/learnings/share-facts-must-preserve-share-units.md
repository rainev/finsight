---
name: share-facts-must-preserve-share-units
description: Share provenance requires the right unit, magnitude, and cross-fact reconciliation; one correctly typed XBRL tag can still be mis-scaled.
metadata: { type: gotcha }
---
Load-bearing share facts must retain their actual XBRL share unit (`xbrli:shares` or the normalized equivalent). A generic balance-sheet point helper that hardcodes USD may reproduce the right number while creating false private provenance.

A correct share unit is necessary but not sufficient. Batch 15 exposed a 1,000× weighted-share
scale error for WAT and a conflicting unqualified share tag for MTD. WAT's cover shares, issued
acquisition shares, EPS, and economic scale supported the corrected denominator. MTD's cover and
dimensioned common-stock counts agreed exactly, while the conflicting unqualified tag was retained
as extraction evidence but excluded from the denominator.

**Why:** Unit identity is part of the source-safety gate, but a correctly typed tag can still have a
bad scale or refer to a different share object. Trusting one tag can move per-share value by orders
of magnitude or create a false withholding.

**How to detect / apply:** Assert the structural row's concept, period, value, and share unit
together. Reconcile cover shares, weighted diluted shares, dimensioned equity-statement shares,
issued/repurchased shares, and EPS scale. If two economically equivalent authoritative facts agree,
retain but exclude a conflicting generic tag with an explicit reason. If the conflict cannot be
resolved, widen or withhold under unreliable shares. Use a unit-aware instant-fact helper for
current shares and keep USD-only helpers limited to monetary facts. See also
[[specialist-facts-require-filed-lineage]].
