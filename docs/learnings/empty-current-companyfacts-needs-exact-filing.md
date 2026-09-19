---
name: empty-current-companyfacts-needs-exact-filing
description: A known latest filing with zero same-accession Companyfacts must trigger exact filing-package extraction before valuation.
metadata: { type: gotcha }
---
SEC submissions can identify the correct current filing while the issuer's Companyfacts endpoint
contains zero facts from that accession, as NEE Q2 2026 and OMC Q2 2026 did. **Why:** attributing
older facts to the current filing creates false period validity; OMC would otherwise have appeared
to use March facts despite a July-filed June quarter and a closed merger. **How to detect / apply:**
count same-accession facts during preflight; when zero, capture and parse the exact filing package
by CIK, accession, form, and primary document before selecting inputs. A complete structural parse
may repair extraction, but it does not itself make post-transaction history economically comparable.

WG39 adds the partial-lag form: INCY Companyfacts contained annual and Q1 2026
interest/operating inputs but not the controlling Q2 facts. A generic TTM
reconstruction therefore ended at the wrong period even though history was not
empty. Rebuild current and comparative YTD revenue, OCF, capex and interest from
the hashed controlling structural filing, then combine them with the latest
eligible annual facts. Never convert a Companyfacts lag into a missing-flow zero.
