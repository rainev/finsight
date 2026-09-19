---
name: post-period-cash-must-project-bridge-assessment
description: A dated post-period cash payment must update both the model input and bridge-quality comparison, or a correct recipe will falsely fail reconciliation.
metadata: { type: gotcha }
---
INCY's June bridge reports $4.535740B cash plus current AFS securities, while the
completed July Vega purchase removes $1.25B before the August valuation cutoff.
The recipe correctly used $3.285740B, but the bridge-quality checker initially
compared that post-event amount with the unadjusted June bridge and rejected the
recipe.

**Why:** model arithmetic and source-quality assessment had different dated
economic perimeters.

**How to detect / apply:** retain the reported period-end bridge unchanged in
the source ledger, bind the completed cash event separately, and project the
same signed adjustment into the bridge assessment before comparing recipe
inputs. Require exact event date, source identity and amount; reject a negative
projected cash balance. Do not apply a contingent maximum, pending agreement or
already reflected period-end payment as a cash adjustment.
