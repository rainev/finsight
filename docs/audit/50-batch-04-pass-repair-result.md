# Batch 04 Pass repair result

**Valuation date:** 2026-08-14

The user approved the four bounded repairs identified in Audit 49. The repaired Batch 04 result is:

- **Pass: 4/10** — MCD, TJX, HD, ROST
- **Conditional: 6/10** — F, GPC, HAS, LOW, NKE, MGM
- **Withheld: 0/10**

| Ticker | Prior base | Repaired base | Final state | Repair |
| --- | ---: | ---: | --- | --- |
| MCD | $153.48 | $154.30 | Pass | Removed generic claims reserve; source-proven no nonzero preferred/NCI claim; documented equity-method investment treatment. |
| TJX | $78.60 | $78.92 | Pass | Replaced stale 2018 revenue with current TTM revenue: $60.372B + $14.323B − $13.111B = $61.584B. |
| HD | $185.42 | $186.48 | Pass | Removed generic claims reserve; source-proven no nonzero preferred/NCI claim; current TTM includes SRS operations. |
| ROST | $136.38 | $137.96 | Pass | Replaced stale 2020 interest with current TTM interest of $43.506M. |

The other six retain their prior Conditional Low ranges and named material dependencies.

## Verification

- Independent Luna-XHigh challenge: **PASS**, no Critical or Important findings.
- Candidate-a/candidate-b byte-identical tree SHA-256:
  `010249c6ee1fc2c32ec5cf2d1fbaa4e83962a19321b91cf87d23b7595cb9c6db`.
- Reclassification report SHA-256:
  `210ae300982152ca4447ab88b94fbf147fc4336adb9c559300c893ea440a6562`.
- Focused repair/artifact suite: **114 passed**.
- Complete backend suite: **1,258 passed, 3 skipped, 1 warning**.
- Frontend production build: **passed**, 1,695 modules transformed.
- Real API: list/detail/calculator 10/10 HTTP 200; default parity 10/10; private leaks 0.
- API receipt SHA-256:
  `9fafbbd34ac8e4acd49201885d623429744f96f5f5082f305c3ed81d13d1081a`.
- Serving artifacts changed: **no**.

## Watchlist

MCD, TJX, HD, and ROST were removed after verified source-bounded recovery. The Recovery Learning
Watchlist now contains 40 companies: 37 Conditional and 3 Withheld. Watchlist contract tests pass
3/3; current SHA-256 is
`2eb4bb21080463a7387c38c3a11ed8c6667ee95c56c5d1afef2e878b41af0ffb`.

No Batch 05 reclassification, Batch 07 work, serving promotion, merge, push, or deployment occurred.
