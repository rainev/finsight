---
name: pse-currency-display-rounds-after-removing-float-noise
description: Normalize floating-point noise before two-decimal PHP display, while keeping source facts and immutable artifact values unchanged.
metadata: { type: gotcha }
---
In Batch 13, LFM's P/B base was mathematically PHP 10.255, but binary multiplication serialized as `10.254999999999999`. The PSE page initially displayed PHP 10.25, one cent below ordinary two-decimal financial rounding. The staged artifact and API calculation were unchanged; only the formatted display was wrong.

**Why:** `Intl.NumberFormat` rounds the actual binary value it receives. A half-cent boundary can fall just below the intended decimal because of floating-point representation.

**How to detect / apply:** Include half-cent products such as `14.65 × 0.70` in browser UAT. Remove sub-cent binary noise in the PSE currency formatter before calling `Intl.NumberFormat`, then verify the real page shows PHP 10.26. Do not change source values, model assumptions, immutable parent artifacts, or manifest hashes merely to repair display rounding.
