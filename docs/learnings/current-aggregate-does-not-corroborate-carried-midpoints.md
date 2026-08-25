---
name: current-aggregate-does-not-corroborate-carried-midpoints
description: A current reported aggregate must not be declared conflicting merely because carried-forward component-range midpoints do not sum to it.
metadata: { type: gotcha }
---
CRM's current structural finance-lease total is $664 million. Its older carried-forward current
and noncurrent lease splits have uncertainty ranges whose midpoints sum to a different amount,
while the combined range still contains the current total. Treating those midpoints as exact
current points falsely blocked the proof-bearing aggregate.

**Why:** A carried-forward component is an uncertainty range, not a current observation. Exact
aggregate-versus-split equality is meaningful only when both split values are current point
facts. Range endpoints may still prove a real impossibility, such as one split's low bound
exceeding the aggregate high bound.

**How to detect / apply:** Keep range-endpoint conflict checks for all usable splits. Sum and
compare split midpoints only when both splits are current, point-valued, and have no
uncertainty. Count a valid aggregate once and retain displaced historical split evidence in
private diagnostics.

