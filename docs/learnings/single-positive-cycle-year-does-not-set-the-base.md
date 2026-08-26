---
name: single-positive-cycle-year-does-not-set-the-base
description: One positive cycle-year cash observation cannot create a positive normalized base when current and median history remain negative.
metadata: { type: gotcha }
---
For highly cyclical and capital-intensive issuers, do not replace a negative current and negative median cash-FCFF history with the lone positive historical year merely to obtain a publishable base. A positive normalized base needs a source-backed through-cycle method and explicit funding coverage for forward commitments; otherwise withhold.

**Why:** In Batch 08, NCLH had negative current TTM cash FCFF and a negative historical median, while one recovery year was positive. Using that single year as base ignored $18.648B of newbuild commitments and manufactured a positive midpoint.

**How to detect / apply:** Compare current, median, percentile, and every annual cash observation. Never let a helper that keeps only positive FCFF silently remove a negative cycle year: Batch 09 initially dropped Target's negative 2023 cash observation and biased its range upward. For cyclical routes, use a loss-preserving history builder and apply the equity floor only after valuation. If a proposed base comes from a lone positive outlier, require an issuer-backed normalization bridge and commitment funding schedule; otherwise withhold. See also [[operating-commitments-need-forward-cash-coverage]] and [[negative-residual-needs-explicit-equity-floor]].
