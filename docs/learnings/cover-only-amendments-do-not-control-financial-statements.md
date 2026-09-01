---
name: cover-only-amendments-do-not-control-financial-statements
description: A latest 10-Q/A may amend only cover metadata; use the underlying full 10-Q for financial facts and the amendment only for the facts it actually changes.
metadata: { type: gotcha }
---
A filing selector that always chooses the newest eligible 10-Q/A can mistake a narrow amendment for
a complete replacement financial filing. The accession, issuer, date, and form are all valid, but
the amendment may contain only one cover-page fact and no income statement, cash flow, or balance
sheet facts.

**Why:** Batch 22 initially selected Honeywell's 2026-07-24 10-Q/A. Its structural wrapper contained
only `EntityCommonStockSharesOutstanding`; the complete 2026-06-30 financial statements remained in
the 2026-07-23 10-Q. Treating the amendment as the whole filing made current operating evidence look
missing even though the issuer had filed it one day earlier.

**How to detect / apply:** Inspect the amendment's fact and statement coverage before treating it as
a full successor. When it is narrow, bind operating and balance-sheet facts to the underlying full
filing and retain the amendment as supplemental evidence only for the fields it actually changes.
Require issuer, report period, accession, filed date, and fact-level lineage for both. Never merge an
amendment into the underlying filing by assuming unchanged values; unchanged values stay sourced to
the original filing.
