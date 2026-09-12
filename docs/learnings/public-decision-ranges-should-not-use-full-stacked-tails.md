---
name: public-decision-ranges-should-not-use-full-stacked-tails
description: Keep simultaneous full-tail corners as private stresses unless evidence supports them; public baseline ranges should use transparent moderated multi-factor scenarios.
metadata: { type: feedback }
---
In Batch 44, applying the historical cash-margin low/high together with the growth, WACC, terminal-growth, dilution and
claim low/high made mechanically valid ranges too wide to support a baseline decision. MPC, for example, spanned
$27.75 to $658.03 around a $260.61 base because every adverse or favorable tail was forced to occur simultaneously.

**Why:** Each tail can be reasonable alone, but their full simultaneous intersection is a remote stress corner, not the
most useful bear/bull decision band. Reproducible arithmetic does not make that corner economically calibrated.

**How to detect / apply:** Report the high/base and low/base ratios and list every scenario dimension that moves. When
several independent tails are stacked without joint evidence, retain that corner privately and present a moderated
multi-factor band using source-linked midpoints between the full tails and unchanged base. Preserve reported bridges,
raw negative residuals and real event/claim stresses; describe the result as a decision range, not a confidence
interval. See [[baseline-decision-is-not-market-prediction]] and [[reporting-honesty]].
