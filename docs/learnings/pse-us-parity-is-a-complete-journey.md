---
name: pse-us-parity-is-a-complete-journey
description: PSE/US valuation parity includes routing, calendar, calculator, holdings, saves, search, and return links—not only visual styling.
metadata: { type: feedback }
---
When the user asks for the PSE UI to be the same as the US valuation experience, treat parity as the complete consumer
journey: market switch, route-based company identity, market-aware header search and valuation dock, seven-day calendar,
five valuation sections, selected-case calculator, manual comparison, save, portfolio, source/history, and return links.

**Why:** A visually similar PSE page still feels broken if search routes to US, PH holdings lose their value/link, or a
saved PSE scenario cannot return to the company. Seamlessness is wiring plus presentation.

**How to detect / apply:** Drive TC-PSE-01 through TC-PSE-06 in `docs/qa/UAT-PLAN.md` against the running app and real
API/database. Preserve the economic distinction in [[pse-market-relative-fallback-is-a-separate-product]].

