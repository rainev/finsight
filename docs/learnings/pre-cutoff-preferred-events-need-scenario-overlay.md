---
name: pre-cutoff-preferred-events-need-scenario-overlay
description: Include completed preferred-stock events in the common-equity claim range before publishing.
metadata: { type: gotcha }
---
A preferred issuance completed before the valuation date is part of the current claim even when it
posts after the controlling balance sheet. Preserve its filing accession and terms, add the claim
once to the preferred scenario range, and keep a later redemption as incomplete until its effective
date passes the cutoff.

**Why:** Batch 34's STT Series L issuance was captured correctly but was initially omitted from the
valuation, overstating common residual value and losing the event's provenance.

**How to detect / apply:** Scan cutoff-safe event receipts after the latest 10-Q, reconcile preferred
proceeds/claims/dividends with common equity, and assert that every load-bearing event accession is
present in the private ledger and scenario inputs.
