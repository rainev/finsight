---
name: sec-inline-html-validation-needs-semantic-tokens
description: Validate SEC event terms semantically because visible currency strings may be split across Inline HTML table tags.
metadata: { type: gotcha }
---
An SEC prospectus can visibly show a complete currency amount while its raw Inline HTML separates
the dollar sign and digits across table cells or markup. A raw substring check for the rendered
string can therefore fail even when the official document contains the exact value.

**Why:** Batch 19's ITW event capture rejected the official 424B5 because `$1,492,470,000` was
rendered from separate HTML cells; the stable numeric token `1,492,470,000` and the filing's
semantic proceeds context were present.

**How to detect / apply:** Validate a small set of stable semantic tokens—issuer, security,
principal, proceeds number, dates, and purpose—without assuming rendered punctuation is contiguous
in raw HTML. Bind the extracted amount and treatment in the receipt, then independently compare it
to the official filing's human-readable context. Never weaken validation to a number alone.
