# Batch 25 HONA Recovery Result

Date: 2026-08-31  
Status: **user-confirmed on 2026-08-31**

## Outcome

The one authorized recovery attempt converted HONA from Withheld to a numeric **Conditional Low**
baseline. Batch 25 therefore moves from Pass 2 / Conditional 7 / Withheld 1 to:

- Pass: **2/10** — IR, OTIS
- Conditional: **8/10** — FTV, DD, CARR, VLTO, GEV, FERG, FDXF, HONA
- Withheld: **0/10**
- Numeric: **10/10**

HONA's recovered range is **$32.663969 / $62.501101 / $102.286548** per share
(bear/base/bull). It is not a clean Pass: the estimate uses reported parent-attributable earnings
from only two comparative half-years and a governed 6x / 8x / 10x earnings range. The prior
comparative period did not bear HONA's new standalone debt interest, while the separated company
opened with $16.006B of debt and negative equity. Those limitations are disclosed and cap the
result at Low reliability.

The route is deliberately equity-level. Parent earnings already include reported interest, so the
model does not subtract debt again through an enterprise-to-equity bridge. Current H1 parent
earnings reconcile to $1.178B pretax - $280M tax - $18M NCI = $880M; prior H1 reconciles to
$1.933B - $295M - $17M = $1.621B. Annualized bear/base/bull earnings are $1.760B / $2.501B /
$3.242B. No market price or analyst target was used.

## Challenge and correction

The preliminary candidate used consolidated after-tax earnings. Independent challenge identified
that HONA reports parent-attributable earnings separately. The final immutable C/D successors
correct NCI treatment and reduce the governed multiples from 6x / 9x / 12x to 6x / 8x / 10x for
the missing prior-period standalone interest burden.

Final independent disposition: **0 Critical / 0 Important**. Source identity was rechecked as HONA,
CIK 0002089271, Form 10-Q accession 0002089271-26-000021, filed 2026-08-05, report period
2026-06-27, inside the 2026-08-14 cutoff. Challenge receipt SHA-256:
`5877be42b85183f1e70c86da9ff1ecd9f1c5129d4e6402eaf1637d7d51415e9c`.

## Verification

- Corrected C/D report SHA-256:
  `11e6d406216d600f3e165772a0798f563e0b08c8250e57f081eb533908808c8a`
- C/D equality: **21/21 files byte-identical**; tree SHA-256
  `9fbb0b1e9e93c59d6830a56ba1e6250b0665ac784b5cb07cb423cee7d8deeca2`
- Focused Batch 25/catalog tests: **17 passed**
- Complete backend suite: **1,625 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated cumulative catalog: **92 available / 149 conditional / 9 unavailable**; 250 total;
  artifact tree `fe5c4566bb422dc7ed165cd81e4a74bdc9f7f3de9002b9818d601cebc99ed9ad`
- Real API: 250 list, 250 detail GET, 250 calculator GET, 250 default-parity checks; 241 numeric
  POST 200, 9 unavailable POST 400, zero private leaks; HONA family `equity_earnings`
- API receipt SHA-256:
  `9fe18c60b92caf580c0ff651adc6025d947fdb289672c80327e53ce5a63f3c24`
- Catalog manifest SHA-256:
  `432fa2312cffd48eefc26ae0ba850ca72122977890cc3a456152b81b9638ce9d`
- Tracked serving artifacts, watchlist, and withheld register remain unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-08-31. HONA entered the Recovery Learning Watchlist as a recovered
Conditional company. The confirmed watchlist is **158 companies** — 149 Conditional and 9
Withheld. HONA did not enter the still-Withheld register because Batch 25 has zero withheld
companies after recovery. Batch 26, serving promotion, merge, push, and deployment remain outside
scope.
