# Batch 09 CLX Recovery Result

Status: **user confirmed on 2026-08-26**. The user authorized one recovery attempt for the
only initially withheld Batch 09 issuer, CLX. No serving promotion, Batch 10, merge, push, or
deployment was performed.

## Outcome

- Pass: **2/10** — BF.B, CL
- Conditional: **8/10** — ADM, STZ, CLX, KO, TAP, TGT, DG, GIS
- Withheld: **0/10**
- Numeric: **10/10**

CLX is recovered as a **Conditional Low** baseline:

| Low | Base | High | Method |
| ---: | ---: | ---: | --- |
| $0.00 | $5.10 | $50.41 | Post-acquisition history-backed cash FCFF |

The $0 bear value is a limited-liability floor after a negative residual-equity calculation. It is
not a missing value and not a prediction that the shares will trade at zero.

## What was fixed

The controlling 2026-06-30 10-K is a split Workiva Inline XBRL filing. Its primary
`clx-20260630.htm` page contains the cover facts and XBRL resources, while
`clx-20260630_d2.htm` contains the financial statements. The official SEC XBRL ZIP already held
both. FinSight now composes those two pages deterministically for the recovery parser.

- Official ZIP SHA-256: `48af9717a35d0b29a425d7e42b594df600ee400d7de6d4b8d1b177f35453798f`
- Primary SHA-256: `a9c51ca4a71091f755c0a7e70762ce29b36dd356ba3b97ea880f9f455e8dedf6`
- Secondary SHA-256: `82a2fc9aa51e0ec6046803bae05cc9cf8b398f0e44012270dffe860e4ff296ed`
- Recovered structural facts: **1,675**

## Conservative model treatment

The DCF uses reported FY2026 revenue of $6.720B and reported cash flow, not the more favorable
$7.331B GOJO pro-forma revenue as its forecast scale. The $476M Glad venture-agreement payment is
disclosed but is not silently added back. The bridge subtracts $1.086B commercial paper, $3.982B
long-term debt, $78M finance leases, and $162M NCI, while adding $143M cash. Operating leases and
$229M supplier finance remain in operating cash conversion and are not deducted twice.

The range uses conservative states bounded by FY2022–FY2026 company history. GOJO integration,
acquisition debt, supplier finance, pro-forma sales weakness, and leverage keep reliability at Low.

## Challenge and verification

The independent challenge caught and resolved two material optimism errors in the first candidate:

1. omitted $1.086B commercial paper; and
2. a favorable $476M one-time cash add-back.

Final evidence:

- independent Luna XHigh re-challenge: **PASS**, no remaining Critical or Important findings;
- focused recovery tests: `3 passed`;
- complete backend suite: `1,305 passed, 3 skipped, 1 warning`;
- two source captures and two recovery runs were byte-identical;
- real FastAPI list/detail/calculator parity: **10/10**, private leaks **0**;
- serving artifacts remained unchanged;
- CLX was added to the Recovery Learning Watchlist as Conditional and was not added to the
  cumulative withheld register.

## Confirmation

The user replied `y` and confirmed the CLX recovery on 2026-08-26. Final Batch 09 is Pass 2 /
Conditional 8 / Withheld 0. Batch 10 requires a separate user signal.
