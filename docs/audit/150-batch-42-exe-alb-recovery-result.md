# Batch 42 EXE/ALB Recovery Result

Date: 2026-09-07
Status: verified recovery result; user confirmed and bookkeeping recorded.

## Exact result

The single authorized recovery attempt covered exactly EXE and ALB. The other eight Batch 42 private/public artifacts
remain byte-identical to the accepted initial candidate.

| Ticker | Initial | Recovery | Low | Base | High | Reliability |
| --- | --- | --- | ---: | ---: | ---: | --- |
| EXE | Withheld | Withheld | — | — | — | — |
| ALB | Withheld | Withheld | — | — | — | — |

Recovered Batch 42 counts remain Pass **0/10**, Conditional **8/10**, Withheld **2/10**, numeric **8/10**.

## EXE attempt

Three non-overlapping post-combination cash windows were reconstructed exactly:

| Window | Revenue | OCF | Capex | Interest | Derived cash-FCFF |
| --- | ---: | ---: | ---: | ---: | ---: |
| H1 2025 reported | $5.886B | $2.418B | $1.220B | $119M | $1.292856B |
| H2 2025 = FY minus H1 | $6.238B | $2.157B | $1.516B | $116M | $733.465M |
| H1 2026 reported | $7.357B | $3.498B | $1.460B | $102M | $2.119305B |

A private conservative DCF challenge produced approximately $2.14 / $47.41 / $147.09 per share, but those values are
not published. The windows cover only 18 months and one is a derived residual period; they do not span a defensible
natural-gas cycle. Twin Eagle also remains signed but unclosed. Its $62.5M deposit is excluded from available cash;
purchase price, financing, projected EBITDA and synergies are not added.

## ALB attempt

The recovery preserved the five-year FCFF margins, whose median remains negative. It then tested the latest positive
year/current improvement without treating either as proven through-cycle cash.

The mandatory-convertible diagnostic reconciles 118,005,057 current common shares + 17,521,000 incremental conversion
shares + 742,000 share-compensation shares = 136,268,057, close to the reported 136,170,000 H1 diluted weighted average.
The $2.235105B preferred principal is not also deducted in this diagnostic. One-to-three remaining quarterly preferred
dividends are reserved separately and reconcile exactly to total diagnostic claims.

The private diagnostic produced approximately $0 / $25.64 / $81.14 per share but is not published. Its positive base
depends on one positive pre-Ketjen year and current cash affected by Talison dividend/working-capital timing, while the
conversion denominator remains a weighted-average proxy rather than a cutoff-date fully diluted count.

## Independent challenge

Two Luna High reviewers independently challenged EXE and ALB before and after implementation. EXE's reviewer verified
every non-overlapping period, Twin Eagle exclusion and DCF replay. ALB's reviewer verified the negative history,
mandatory-conversion arithmetic, preferred principal/dividend non-overlap and public withholding. Sol added exact claim
reconciliation coverage. No Critical or Important implementation finding remains.

## Determinism and verification

- Recovery candidates: `output/batch-42-recovery-run-c-20260907` and
  `output/batch-42-recovery-run-d-20260907`; all 21 files are byte-identical.
- Candidate tree SHA-256: `26d252c77b78f6ecf26362cd127c9220905b5301628625326556e33a6909faaa`.
- Recovery report SHA-256: `09c9dee28fa5d0438f34557e6a8675190d3d6b0226a7df43e9d11541554f10f5`.
- Focused Batch 42 initial/recovery tests: **14 passed**.
- Complete backend regression: **1,700 passed, 3 skipped, 1 warning** (223.58 seconds). The warning is the existing
  Python `crypt` deprecation in passlib.
- Frontend production build: passed, 1,694 modules. No UI behavior changed.
- Cumulative recovery catalog: 420 companies — 116 available / 287 conditional / 17 unavailable; 403 review-required /
  17 withheld.
- Catalog artifact-tree SHA-256: `0554a0d2480bfbba269ab829132f46e6a02f9755ae4e3cfeb2d62d110dda54f0`.
- Catalog manifest SHA-256: `0ac2cd2799ebf46f8ef1c4cff92ad2438c01f15856a1c6c57c03e2bfd7e7d69d`.
- The catalog exactly preserves all 410 confirmed predecessor artifacts and copies all ten Batch 42 recovery public
  artifacts; every source audit path resolves.
- Real API: 420 list entries, 420 detail/calculator GETs, 420 expected calculator outcomes, exact list/detail parity,
  zero private leaks and zero forbidden serving imports.
- Calculator API receipt SHA-256: `0774e4038d8b765275db7076ac709a953335cdd2d4080743bc4e3042f3f6cf71`.
- Exact API/import receipt SHA-256: `05ad2366d264f608ff53e3b8b30a531c02cddb79b748f6127e7d5378cda5c77c`.

## Confirmation boundary

The user confirmed this recovery result. The Recovery Learning Watchlist now contains **304 entries**: 287 Conditional
and 17 Withheld after recovery. The cumulative withheld register contains **27 entries**. EXE and ALB each have exactly
one consumed automatic recovery attempt.

- Confirmed Recovery Learning Watchlist SHA-256: `d8d4204002d62a95777ee06654fb23c5a5448101d1314e2d81c54bd8f6e92043`.
- Confirmed cumulative withheld-register SHA-256: `9b33f8654428a333c90d228c14a1002c5cb601406882622b737805d4da2a6ed1`.
- Confirmation/bookkeeping verification: **20 passed** across the register and Batch 42 contracts.

Tracked serving artifacts remain unchanged. Batch 43, merge, push and deployment remain untouched.
