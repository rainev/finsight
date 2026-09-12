---
name: exact-period-ends-outrank-fiscal-year-labels
description: Select annual SEC history by exact duration and period end because issuer fiscal-year labels can be wrong.
metadata: { type: gotcha }
---
When reconstructing annual filing history, use the controlling accession, exact start/end dates, and
an annual-length duration before trusting an XBRL fiscal-year label. Key observations by their exact
period end and retain only one value for each economic period.

**Why:** Batch 33's WRB filing facts contained misleading fiscal-year labels even though the
accessions and exact annual periods were usable. Selecting by label would have omitted or assigned
the wrong historical year and distorted the reported earnings range used to bound residual income.

**How to detect / apply:** Filter cutoff-safe 10-K facts to roughly 300–380-day durations, require
exact period dates, deduplicate by period end, and preserve the accession and filed date. Treat
fiscal-year/form labels as supporting metadata, not as the controlling period identity.
