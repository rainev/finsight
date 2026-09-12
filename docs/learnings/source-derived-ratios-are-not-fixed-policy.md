---
name: source-derived-ratios-are-not-fixed-policy
description: Microsoft practical output overwrites a policy ratio with a source-derived result; compile the underlying rule instead.
metadata: { type: gotcha }
---
Microsoft's retained practical forecast contains sales-to-capital 1.557896542659304,
but the retained diagnostic assumption is 3.0. The practical ratio already includes
the historical/current capex-intensity multiplier. Copying it into a refresh policy
freezes old evidence and loses the bull adjustment.

Compile the underlying diagnostic anchor and recompute the approved capex rule on new
source periods. Record both in the ledger. Check every scenario independently.
An old margin can also equal several different medians: arithmetic equality does not
prove a four-year policy. Use the approved history rule and label any normalization
delta separately from frozen legacy recipe replay.

The same trap applies to history-bounded revenue growth. Read the retained
generator's floors/caps, verify them against every frozen scenario, then bind
them to newly reconstructed revenue-growth history. The common history rule
uses min/median/max below four observations and quartiles from four onward;
the retained observation count must not freeze that choice for later filings.
