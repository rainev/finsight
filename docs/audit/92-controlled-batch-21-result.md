# Controlled Universe Reset Batch 21 Initial Result

Status: **firsthand verified and user-confirmed on 2026-08-31**. Exactly ten frozen issuers were
processed at 2026-08-14. Confirmation added five Conditional issuers to the watchlist. No recovery,
withheld-history mutation, promotion, Batch 22, merge, push, or deployment.

## Outcome

- Pass: **5/10** — EME, GWW, CSX, EXPD, FAST
- Conditional: **5/10** — RTX, LHX, TXT, NSC, JBHT
- Withheld: **0/10**; Numeric: **10/10**; Reliability: **10 Low**
- Cumulative: **76 Pass / 125 Conditional / 9 Withheld; 201/210 numeric**

| Ticker | Outcome | Low | Base | High | Simple reason |
| --- | --- | ---: | ---: | ---: | --- |
| RTX | Conditional | $35.74 | $72.85 | $124.62 | Engine inspections/compensation and claim tail |
| EME | Pass | $217.12 | $435.86 | $668.04 | Backlog cash history and complete bridge |
| LHX | Conditional | $69.08 | $152.47 | $263.63 | Aerojet integration and redeemable preferred NCI |
| TXT | Conditional | $36.58 | $71.32 | $149.02 | Mixed manufacturing/captive-finance equity model |
| GWW | Pass | $286.93 | $484.20 | $723.87 | Distribution cash history and complete bridge |
| CSX | Pass | $7.34 | $14.86 | $31.27 | Rail cash history and complete debt/lease bridge |
| NSC | Conditional | $26.51 | $80.69 | $180.46 | Standalone rail value; Union Pacific deal separate |
| JBHT | Conditional | $6.27 | $41.17 | $154.92 | Trucking/intermodal cycle and reinvestment |
| EXPD | Pass | $52.56 | $90.53 | $207.20 | Debt-free forwarding cash baseline |
| FAST | Pass | $9.02 | $14.87 | $22.71 | Industrial-supply cash history and complete bridge |

## Evidence

- Controlling accessions: RTX `0000101829-26-000027`; EME `0000105634-26-000110`; LHX
  `0000202058-26-000058`; TXT `0000217346-26-000036`; GWW `0000277135-26-000079`; CSX
  `0000277948-26-000032`; NSC `0001628280-26-049326`; JBHT `0001437749-26-024397`; EXPD
  `0001193125-26-334457`; FAST `0000815556-26-000041`.
- Capture: **4 reused / 6 fetched** in packet and structural layers; replay A/B reused 10/10.
- Independent challenge: 10/10, **0 Critical / 0 Important**; SHA-256
  `3fe189dae71c0670295d97718d88ea78a1421b051356bb98baea4c245a66234b`.
- Deterministic hashes: source `96cc39d5a028f310e9ad18be7260cb1790195bdfad3f5aa5ee8a9d80d6867ad3`;
  structural `859b8c351ebfc1e782f87cc91a57471a67b74cd657cd3b1bdbb3492774ada874`;
  candidate `4d6c83b4e1cdee231cd0bfcdfdbd7b3c37828b85a69ba0f890bb5a46e4131455`;
  private `127aa521d64eb23b6ac5655c02adaf3c3267f9260f9a58114c01a482f59ca0f6`;
  public `c385931773968e92d432aebd442f4f6ece8764d6b09e80ba2d3ca11a92ce1e5b`.
- Focused tests: **7 passed**. Full backend: **1,580 passed, 3 skipped, 1 warning**.
- Frontend production build: **1,694 modules**, passed.
- Real isolated FastAPI: 210 list/detail/calculator parity; 201 numeric POST 200; 9 unavailable
  POST 400; Batch 21 stage parity 10/10; private leaks 0. API receipt SHA-256
  `d7282d07e019fef75f8409baacc8a3d79498b17f081d5f6a6c77d86fccbe3de3`.
- Catalog: 76 available / 125 conditional / 9 unavailable; artifact tree
  `da438cc881f575ee20ec9b128942dc84d0f5a508a87065cc11e79556e181b35b`;
  manifest `f7c0d9c62da775f3d98325caba3631d30940d5fc3eb9e0a8faad137090e418b6`.
- Watchlist is 134 (125 Conditional / 9 Withheld), SHA-256
  `2cf1f72ff67650fc936c20676fa31af586c803e32a4f31dd489f82c1aff7ca12`; withheld history remains 19
  (`28bcfd...f3ec`). Tracked serving roots are unchanged. No subagents were used.

The user replied `y` on 2026-08-31. No recovery is needed. Batch 22 was not started; the next valid
signal is `Start Universe Reset Batch 22`.
