---
name: sec-archive-url-uses-accession-owner-cik
description: Build an SEC filing URL with the accession owner's archive CIK when a successor issuer reuses a predecessor filing.
metadata: { type: gotcha }
---
In Batch 44, ExxonMobil Holdings Corp used successor CIK `0002115436`, but the controlling Q2 2026 filing retained
accession `0000034088-26-000093` under legacy archive CIK `0000034088`. Building the public SEC URL from the current
manifest CIK produced a plausible but invalid `/data/2115436/` path; the correct archive path uses `/data/34088/`.

**Why:** Issuer identity and filing-archive ownership can diverge during a holding-company succession. The valuation
still belongs to the successor, while the immutable source document remains stored under the predecessor CIK.

**How to detect / apply:** Derive the archive URL from the accession owner or verified package source, not blindly from
the current issuer manifest. Keep current issuer CIK, source accession CIK, continuity basis, and public URL as separate
fields; test that the final URL matches the captured primary document. See [[xbrl-context-entity-outranks-wrapper-identity]]
and [[sec-issuer-identity-is-not-exact-display-name]].
