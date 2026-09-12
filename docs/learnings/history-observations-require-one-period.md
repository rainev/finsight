---
name: history-observations-require-one-period
description: A normalized history observation may not mix revenue and cash-flow inputs from different period ends.
metadata: { type: gotcha }
---
A history ratio must describe one coherent economic period. Never label a cash-conversion margin as
TTM at a newer date when its numerator still comes from an older filing and only its revenue
denominator was refreshed.

**Why:** Batch 32's first LITE successor paired June 2026 earnings-release revenue with March 2026
TTM OCF/capex/interest and labeled the resulting ratio as a June observation. The valuation's
governed margins did not depend on that hybrid, but the private evidence was still false.

**How to detect / apply:** Assert that every input to a historical observation shares the same
period end. If a later release reports revenue and bridge facts but omits cash flow, keep the last
coherent revenue/cash pair in the history profile and store the newer revenue only in the valuation
state and event ledger. Explicitly label the older cash anchor; never move its period date forward.
