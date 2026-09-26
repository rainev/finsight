---
name: pse-relative-calculators-must-support-sub-one-book-multiples
description: PSE P/B and P/S calculator controls must allow legitimate multiples below 1.0 and reproduce their published baselines.
metadata: { type: gotcha }
---

# PSE relative calculators must support sub-one book and sales multiples

## Context

Phase B Batch 3 introduced P/B-to-reported-NAV screening ranges with legitimate multiples below 1.0. Batch 16 reused a 0.10×/0.15×/0.20× P/S band for stressed FOOD and SFI screens.

## Failure

The shared market-relative calculator originally applied a minimum editable multiple of 1.0. The Batch 3 P/B repair allowed sub-one P/B but still left P/S with a 1.0 minimum and a 0.30 maximum for the new band. The SFI edited-case test raised `valuation_multiple must be between 1.0 and 0.30000000000000004` even though its published base was 0.15×.

## Durable rule

Set calculator bounds from the metric family, not only from the generic `multiple` relation:

- P/B and P/S screens may use editable multiples down to 0.05 and a 0.05 step for the reviewed current bands.
- P/E and other reviewed higher-multiple screens retain the 1.0 floor and 0.25 step unless their policy requires otherwise.
- The calculator must reproduce every published baseline before a staged catalog can pass its gate.
