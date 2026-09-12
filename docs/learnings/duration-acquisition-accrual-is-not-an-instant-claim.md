---
name: duration-acquisition-accrual-is-not-an-instant-claim
description: An accrued-but-unpaid acquisition amount with a duration context needs a carrying-balance and cash-overlap bridge before equity deduction.
metadata: { type: gotcha }
---
REGN reports acquisition contingent consideration accrued but not yet paid in a
six-month supplemental noncash table. That wording does not change the XBRL fact
into a period-end balance-sheet fact.

**Why:** The amount may overlap a broader accrued-liability balance, investing
cash payments or OCF working-capital movements. Treating it as an instant claim
can double deduct cash or liabilities.

**How to detect / apply:** Preserve the start/end dates and classify the row as a
duration accrual. Require a current carrying-liability reconciliation and explicit
cash/OCF overlap rule before using it in the enterprise-to-equity bridge. Missing
proof remains review, never zero.
