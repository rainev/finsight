---
name: structural-approvals-expire-with-controlling-accession
description: A reviewed structural-XBRL decision is valid only for its exact controlling accession and must be rerun when a newer cutoff-eligible filing takes control.
metadata: { type: gotcha }
---
The controlled Batch 01 refresh selected newer filings for AAPL, ANET, WDC, JPM, and O than
the accessions used by older review evidence. The fresh offline structural run therefore did
not inherit earlier accepted decisions: across 19 current requests it accepted only CRM's
exact $664 million finance-lease total and left the rest rejected or unresolved.

**Why:** Concept availability, dimensions, periods, economic scope, and balances change by
filing. Reusing an old allowlist fingerprint against a new controlling filing would silently
mix periods or treat absence in the new filing as an old zero.

**How to detect / apply:** Bind every structural approval to ticker, CIK, accession, filed
date, period, form, concept, unit, value, mapping version, and reason codes. When the
controlling accession changes, rerun extraction and review; never auto-promote the prior
decision. Link with [[specialist-facts-require-filed-lineage]].

