---
name: cutoff-freshness-includes-earnings-releases
description: Scan cutoff-safe 8-K earnings releases and material events after the controlling 10-Q before freezing a valuation bridge.
metadata: { type: gotcha }
---
A latest 10-Q is not necessarily the latest cutoff-safe economic state. Before freezing a batch,
scan every issuer's submissions through the valuation date for 8-K earnings releases, debt events,
capital changes, and material agreements. Capture and hash the primary filing and relevant exhibit.

**Why:** Batch 32 initially valued LITE and SNDK from their controlling Q3 10-Qs even though cutoff-
safe August 8-K exhibits reported later full-year revenue, cash, debt, securities, and share counts.
Those releases materially changed both ranges. GDDY, HPE, and AVGO also had post-balance financing,
dividend, asset-sale, tender, and customer-agreement evidence that belonged in the event ledger.
Batch 35 showed the complementary case: JKHY's August 8-K reported only non-recurring deconversion
revenue, so it belonged in the ledger and warning but could not replace March GAAP earnings. The
same ten-company screen also found WMB's JV financing and CFG's Series J preferred issuance.
Batch 41 exposed a separate capture trap: Halliburton's Exhibit 99.1 used the generic filename
`livemastererdocument.htm`. A filename-only filter missed it even though the primary 8-K explicitly
identified the exhibit relationship.

**How to detect / apply:** After selecting the controlling 10-K/Q, scan subsequent `8-K` rows up to
the valuation cutoff. Treat an earnings release as a newer operating/bridge snapshot only for the
fields it actually reports; do not invent missing cash-flow fields. Reconcile debt/cash/share events
into arithmetic when material, or document why they are net-neutral/nonbinding. Hash every relied-
upon document and invalidate the valuation when a later material event cannot be bounded. Persist
one accepted/rejected screening receipt per issuer; a missing receipt is not proof that no event
exists. Discover candidate exhibits from the filing's document/relationship metadata or primary
document links, then validate type and content; do not require filenames to contain `99`, `exhibit`,
or `release`.
