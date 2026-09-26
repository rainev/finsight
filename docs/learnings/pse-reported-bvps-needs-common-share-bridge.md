---
name: pse-reported-bvps-needs-common-share-bridge
description: PSE summary BVPS may disagree with equity scope and dated ordinary shares; independently bridge the denominator before publishing a per-share screen.
metadata: { type: gotcha }
---
PSE company financial-summary BVPS is not automatically parent ordinary-common BVPS. In Batch 19, LODE's June 2026 page printed PHP0.80, but PHP225,367,129 total equity divided by 3,000,000,000 outstanding common shares is about PHP0.0751; PAX's PHP5.97 likewise did not reconcile to reported parent equity and stock-page common shares. Minority equity, preferred claims, treasury or denominator timing can also matter.

**Why:** A positive P/B range built on the printed figure alone can be wrong by multiples, even while the source page and model arithmetic each look plausible in isolation.

**How to detect / apply:** Preserve the original BVPS, equity scope and units, period, dated shares, and source links. Independently divide the appropriate equity numerator by all relevant outstanding ordinary shares (not just listed shares). If the remaining gap or capital claims cannot be explained, publish a null blocked result; if a transparent total-book proxy is used, label it Low reliability and never intrinsic.
