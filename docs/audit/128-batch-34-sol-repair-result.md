# Batch 34 Sol Audit Repair Result

Date: 2026-09-03
Status: **user-confirmed on 2026-09-03**

## Outcome

All verified Important and Minor findings from Audit 127 are repaired. The model-suitability lead was
resolved conservatively: USB remains Pass, while BRO returns to Conditional Low because its
acquisition/reinvestment program is material and not yet bounded as recurring versus exceptional.

- Pass: **1/10 — USB**
- Conditional: **9/10 — L, SPGI, NTRS, BRO, PGR, TRV, KEY, TFC, STT**
- Withheld: **0/10**
- Numeric: **10/10**

| Ticker | Outcome | Low | Base | High | Reliability |
| --- | --- | ---: | ---: | ---: | --- |
| USB | Pass | $26.88 | $41.91 | $56.67 | Medium |
| L | Conditional | $61.27 | $94.25 | $124.30 | Low |
| SPGI | Conditional | $83.49 | $138.03 | $185.93 | Low |
| NTRS | Conditional | $48.76 | $77.54 | $106.43 | Low |
| BRO | Conditional | $27.25 | $44.90 | $63.70 | Low |
| PGR | Conditional | $43.72 | $80.70 | $121.92 | Low |
| TRV | Conditional | $115.90 | $201.10 | $291.32 | Low |
| KEY | Conditional | $10.46 | $16.71 | $22.95 | Low |
| TFC | Conditional | $32.22 | $49.88 | $67.05 | Low |
| STT | Conditional | $63.29 | $97.73 | $131.30 | Low |

## Repairs completed

- USB's public artifact now identifies the actual residual-income model and no longer exposes an
  FCFF model or bridge. Its private baseline, public availability, and reliability agree. Its
  capital evidence is runtime-bound to the controlling filing receipt, package, HTML, and hashes.
- Repricing now recomputes reliability, common-equity periods, reported ROE, modeled ROE caps,
  scenario traces, and baseline metadata. Public artifacts contain no
  `RELIABILITY_PAYLOAD_INVALID` fallback.
- Beginning and current preferred claims are separate and source-linked: TFC `$4.916B/$5.411B`,
  NTRS `$884.9M/$884.9M`, and STT `$3.559B/$4.059B`. STT's Series L event is recorded once.
- L/SPGI derived parent-earnings rows now carry USD units.
- Recovery execution pins the exact confirmed Batch 34 report hash, denominator order, and
  `0 Pass / 10 Conditional / 0 Withheld / 10 Numeric` input state.
- Recovery paths now distinguish an implemented repair from an assessed-but-pending repair. The
  final source-audit receipt no longer describes repaired NTRS/STT claims as missing.
- Public/list verification now includes `availability_type`, `confidence`, and immutable catalog
  metadata, so exact list parity is meaningful rather than a schema mismatch.
- Audit index confirmation statuses were reconciled.

## BRO model challenge

BRO remains on the residual-income/equity-earnings route; a simple MRSH-like FCFF route is not
economically suitable. Source history shows `$1.754B` of TTM cash-FCFF before acquisitions, but
approximately `$7.723B` of TTM acquisition cash. In 2025 it completed 43 acquisitions, paid
`$7.854B`, and reported `$5.902B` revenue versus `$6.947B` pro-forma revenue. Treating acquisitions
as recurring reinvestment makes cash-FCFF deeply negative; ignoring them produces a large positive
range. The residual-income number remains useful, but Pass is not defensible until this acquisition
program is bounded.

## Independent challenge

Two independent Luna reviews challenged the exact E/F successor after repair. Final disposition:
**0 Critical / 0 Important / 0 Minor**. All 30 scenarios replay exactly, source/event claims and
periods reconcile, public semantics match the private model, and no private evidence leaks.

## Determinism and real-consumer verification

- Final E/F: 21/21 files byte-identical; tree
  `9a68cd34284609d256c33c80f7a6479dce8c99f5e3dc043010cf8f02ecf9fb0d`
- Recovery report SHA-256:
  `5d718233b47b1222495f9bb73cc748e643636449c2b610bb35f1c9b158ece6e7`
- Post-repair source audit SHA-256:
  `a1110d0e0683928bddf905894964406b107bf241e88b3971006758479ef1a709`
- Focused Batch 34 tests: **17 passed**
- Complete backend suite: **1,586 passed, 3 skipped, 1 warning**
- Frontend production build: **1,694 modules**, passed
- Isolated repaired catalog: **340** — 116 available / 214 conditional / 10 unavailable; artifact
  tree `48d9d77b2adb61415e22d44030a675280c9bf936fab2cd205674553bce030740`
- Real API: 340 list, 340 detail, 340 calculator/default parity; zero private leaks
- Exact list parity: true; detail parity: 340/340; forbidden serving imports: 0
- Calculator/API receipt:
  `7b6095a9d59c8348b9a36b657740e36aa5ef7480480ab84e1d5fa1b652ec480a`
- Exact-list/detail/import receipt:
  `0f2b87ca5227e4393494bd9d8eb2132006fa97404df1bc76a4cc96051fef60fd`
- Catalog manifest:
  `c50870bfd0b8ff7652607a77ce0f7e81403d4c7c434fe803d2aaf89a0dbb2dd7`
- Watchlist before this confirmation was **223** — 213 Conditional / 10 Withheld; SHA-256
  `70b814e96e4d4e36a2bb45b0dca7d5ea1ee024eee09ee238218f52d82eebb294`
- After confirmation, BRO was returned to the Recovery Learning Watchlist. It now contains **224**
  entries — 214 Conditional / 10 Withheld; SHA-256
  `ec861afc1778e7de157ad40478b9b2f90fa49e9205d2432c2d4ea344a4e581b7`
- Withheld register remains unchanged; SHA-256
  `7530586e01fdf65a61eea35feeca4b47337bc19134caeb4a87e4e8a87a016fce`
- Existing tracked serving data remains unchanged.

## Confirmation and bookkeeping

The user replied `y` on 2026-09-03. BRO was returned to the Recovery Learning Watchlist because it
is Conditional after the Sol repair; USB remains outside the watchlist because it passed. The list now
contains **224 companies — 214 Conditional / 10 Withheld**. No withheld-register change was required.

Batch 35, serving promotion, merge, push, and deployment remain outside this repair.
