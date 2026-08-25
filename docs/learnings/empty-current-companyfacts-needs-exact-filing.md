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
