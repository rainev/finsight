---
name: recipe-migration-is-not-refresh-readiness
description: Require both exact scenario replay and source refresh bindings before activating the automated catalog.
metadata: { type: gotcha }
---

The 2026-09-08 automated migration can replay many historical FinSight scenarios from private packets, but those packets often record resolved numbers rather than reusable selectors for the next filing. Matching all three published values proves arithmetic preservation, not quarterly updateability.

**Why:** Treating a replayable recipe as a refresh policy would silently carry forward old cash, debt, claims, shares, or economic-event assumptions.

**How to detect / apply:** Keep separate recipe-ready and refresh-policy-ready counts. The one-command workflow must fail closed before activation while either migration is incomplete. Exercise successive actual filings, including company-specific claims, before certifying a refresh policy. Do not replace missing implementation with mass unavailable records.
