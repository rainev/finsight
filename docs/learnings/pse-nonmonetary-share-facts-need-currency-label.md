---
name: pse-nonmonetary-share-facts-need-currency-label
description: PSE reported-fact storage requires a non-null currency string even for ordinary-common share counts; keep shares as the unit and label currency not applicable.
metadata: { type: gotcha }
---
During Batch 16, the reviewed-fact loader tried to insert an original `reported_common_shares_outstanding` fact with `currency=NULL`, `unit_scale=shares`, and `measurement_type=stock`. Postgres rejected it because `pse_reported_facts.currency` is non-null; earlier batches had stored only monetary facts. Replaying the same receipt after setting the non-monetary currency label to `N/A` succeeded, and the persistence verifier confirmed 22 original-period facts without deleting partial rows.

**Why:** A share count is not money, but the generic reported-fact table requires a currency field. Inventing PHP or USD would misstate the source unit; leaving it null fails at runtime.

**How to detect / apply:** For future share-count facts, preserve the original count and `unit_scale=shares`, use `currency=N/A` as the explicit non-monetary sentinel, keep the as-of date and ordinary-common scope, then verify the stored row against the PSE share source. Do not coerce shares to PHP millions or treat failed partial evidence loading as authorization to delete rows; use the idempotent loader replay.
