---
name: pse-company-page-does-not-prove-current-listing
description: A live PSE company and financial-summary page can survive delisting; confirm the security's current exchange status before freezing a listed-common batch.
metadata: { type: gotcha }
---
During the 2026-09-23 Batch 15 review, 8990 Holdings (`HOUSE`) still had a PSE company profile and a 1H2025 financial-summary page, which made it look eligible at proposal time. The [PSE delisting notice](https://edge.pse.com.ph/downloadHtml.do?file_id=1827603) says its common shares were delisted effective 2025-10-31. The confirmed frozen batch kept HOUSE as a blocked/null record rather than silently substituting another ticker or publishing a stale listed-equity screen.

**Why:** Historical company pages are a source archive, not proof that an ordinary common security is currently listed or tradable.

**How to detect / apply:** Before proposing a PSE batch, cross-check current listing/stock status and later exchange notices, especially where a financial summary is stale. At processing time, let a verified delisting notice override the apparent presence of a company page. Preserve the exact confirmed set as blocked/null when a ticker is out of scope; record the security as delisted and disable its calculator. See [[pse-blocked-artifacts-need-disabled-calculator-and-page]].
