---
name: scenario-margin-stress-is-not-reported-cash
description: Batch 6 BBY/DECK/DRI margin haircuts are governed forecast stresses, not reported working-capital movements.
metadata: { type: gotcha }
---
The retained Batch 6 generator subtracts scenario rates from the historical
cash-conversion margin, then applies a 0.001 margin floor. BBY uses
0.015/0.005/0, DECK 0.02/0.005/0, and DRI 0.01/0.003/0. These rates are policy
assumptions, not extracted cash amounts. A generic raw-history margin binding
silently loses them; calling them reported working-capital adjustments is also wrong.

Compile the declared rates and verify the formula against the retained generator
and every original recipe scenario. Preserve reported OCF/capex and raw history
separately; apply the stress only to the scenario margin. Public assumptions must
show the applied margin while explaining the policy stress, not overwrite it with
the raw historical metric. This does not validate financing or other bridge claims.
