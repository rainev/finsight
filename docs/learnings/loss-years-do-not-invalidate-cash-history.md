---
name: loss-years-do-not-invalidate-cash-history
description: Complete cash history can remain usable when loss years use an approved tax fallback and profitable years retain reported rates.
metadata: { type: gotcha }
---
CRWD has five complete annual revenue, OCF, capex and interest periods, but only
two have positive pretax income. Requiring three positive-tax-rate observations
discarded the otherwise complete history even though the normalizer already
defines a 21% fallback for loss years.

**Why:** A minimum count for cash observations and a minimum count for usable
profitable-year tax rates are different tests. Treating them as one test can
systematically reject companies with genuine loss years or tempt a caller to
invent a positive tax rate.

**How to detect / apply:** Keep every complete cash period, calculate reported
tax rates only when pretax income is positive and periods align, and apply the
approved loss fallback only to loss periods. A versioned issuer rule may lower
the profitable-period minimum when multiple reported profitable years remain;
it must not fabricate tax facts or erase the loss observations.
