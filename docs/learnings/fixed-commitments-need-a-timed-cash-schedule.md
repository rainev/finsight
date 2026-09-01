---
name: fixed-commitments-need-a-timed-cash-schedule
description: Model a fixed multi-year commitment as scheduled payments or an equivalent present-value reserve, not a permanent cash-margin reduction.
metadata: { type: gotcha }
---
A disclosed fixed commitment with a stated total cannot be described as paid over several years if
the implementation merely subtracts one annual amount from starting cash flow and then grows that
lower amount forever. Model the annual payments for the exact governed duration or subtract their
scenario-specific present value once from enterprise value.

**Why:** KLAC's $5.970B purchase commitment was initially represented by subtracting $1.990B /
$1.194B / $746.25M from starting FCFF for the bear/base/bull cases. Because the shared DCF grows
starting FCFF through the terminal period, that treatment made a 3/5/8-year commitment behave like
a perpetual margin reduction.

**How to detect / apply:** compare the narrative timing to the model trace. For a total commitment
`C` paid evenly over `N` years, calculate `annual = C/N` and
`PV = sum(annual / (1 + discount_rate)^t for t=1..N)`. Record the total, duration, annual payment,
discount rate, and PV in each scenario. The PV reserve is mathematically equivalent to an explicit
year-by-year schedule when the commitment does not continue into terminal cash flow. See also
[[commitment-warnings-must-bind-cash-arithmetic]].
