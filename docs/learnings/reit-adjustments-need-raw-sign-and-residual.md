---
name: reit-adjustments-need-raw-sign-and-residual
description: Preserve issuer-reported adjustment signs while normalizing economic direction and reconciling AFFO.
metadata: { type: gotcha }
---
REIT supplements often present deductions in parentheses. Passing those negative values into a formula that already subtracts straight-line rent or recurring capex reverses their effect.

**Why:** Realty Income's filed Q1 2026 supplement reports straight-line rent/expenses and recurring capex as negative reconciliation rows, while FinSight's mechanical adapter expects nonnegative amounts to subtract.

**How to detect / apply:** Retain raw signed values, normalize adjustment magnitude/direction separately, identify the exact current-period column, and reconcile reported FFO-to-AFFO arithmetic. Any unexplained residual remains unresolved; never force the issuer's AFFO definition into a standardized formula.
