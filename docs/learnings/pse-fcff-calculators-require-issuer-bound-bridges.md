---
name: pse-fcff-calculators-require-issuer-bound-bridges
description: Every PSE FCFF calculator must read cash, debt, claims, and shares from the selected issuer artifact, never the AP seed.
metadata: { type: gotcha }
---
The shared PSE FCFF calculator originally loaded AP's cash, debt, and shares for every intrinsic issuer. A non-AP
artifact could therefore display its own baseline but recalculate edits with AP's capital bridge and denominator.

**Why:** A calculator response can look directionally reasonable while being economically tied to the wrong company.
Baseline artifact tests alone do not detect this mismatch.

**How to detect / apply:** Every new FCFF artifact must publish a reviewed `capital_bridge` containing issuer-specific
cash, debt including the stated lease treatment, claims, and shares. Calculator tests must reproduce each artifact's
default and prove at least two issuers have distinct bridges and share counts. AP may retain an explicit legacy fallback,
but no other issuer may use it. Recheck `backend/app/pse_valuation/calculator.py` before relying on this learning.
