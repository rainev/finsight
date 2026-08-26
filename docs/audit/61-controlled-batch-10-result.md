# Controlled Universe Reset Batch 10 Result

Status: **user confirmed on 2026-08-26**. Exactly ten frozen Consumer Staples issuers were
processed at the 2026-08-14 cutoff. MKC, SJM, and TSN were added to the Recovery Learning
Watchlist. No serving promotion, Batch 11, merge, push, or deployment was performed.

## Result

- Pass: **6/10** — HSY, HRL, KR, PEP, PG, WMT
- Conditional: **3/10** — MKC, SJM, TSN
- Withheld: **1/10** — KMB
- Numeric: **9/10**

| Ticker | Outcome | Low | Base | High | Reliability | Controlling filing / period |
| --- | --- | ---: | ---: | ---: | --- | --- |
| HSY | Pass | $86.55 | $144.42 | $200.50 | Low | `0001628280-26-050900` / 2026-06-28 |
| HRL | Pass | $8.56 | $15.99 | $26.07 | Low | `0000048465-26-000026` / 2026-04-26 |
| KMB | Withheld | — | — | — | — | `0001628280-26-052348` / 2026-06-30 |
| KR | Pass | $13.77 | $46.81 | $89.65 | Low | `0001104659-26-078236` / 2026-05-23 |
| MKC | Conditional | $6.94 | $19.69 | $43.96 | Low | `0000063754-26-000274` / 2026-05-31 |
| PEP | Pass | $31.59 | $67.43 | $111.81 | Low | `0000077476-26-000035` / 2026-06-13 |
| PG | Pass | $53.08 | $78.51 | $107.10 | Medium | `0000080424-26-000103` / 2026-06-30 |
| SJM | Conditional | $16.18 | $48.37 | $119.08 | Low | `0000091419-26-000050` / 2026-04-30 |
| TSN | Conditional | $6.06 | $25.30 | $43.39 | Low | `0000100493-26-000058` / 2026-06-27 |
| WMT | Pass | $13.61 | $22.67 | $34.37 | Low | `0000104169-26-000102` / 2026-04-30 |

Values are USD per-share baseline decision ranges, not predictions or recommendations. Pass means
the source identity, current bridge, model, and history are complete enough for a normal baseline;
it does not mean the market outcome is predictable.

## Important treatments

- HSY's $5.189135B total long-term debt already includes $75.541M finance leases. Only its
  $421.545M short-term debt is added; Class B is included through the as-converted 203.25M diluted
  denominator and is not added twice.
- HRL uses $2.856339B total lease-inclusive debt once and adds only $33.107M current marketable
  securities to cash.
- KR includes $1.264B current plus $15.731B noncurrent lease-inclusive debt. The terminated
  Albertsons transaction is not treated as a continuing combination.
- PEP's $10.602B short-term-debt total already includes commercial paper. Equity-method affiliates
  remain inside operating cash conversion rather than being added again as excess cash.
- PG's 2.4225B diluted shares already include 68.3M assumed preferred-conversion shares. The $756M
  preferred carrying value is therefore diagnostic and is not subtracted again.
- WMT includes $58.129B debt/finance leases and $6.645B NCI/redeemable NCI once. Supplier finance
  and operating leases remain operating cash items.
- MKC is Conditional because McCormick de Mexico became consolidated during 2026; its $577.7M NCI
  and a conservative carried $95M finance-lease claim are included.
- SJM is Conditional because the Hostess/Sweet Baked Snacks impairment, divestitures, leverage,
  restructuring, and loss-year tax policy make history less comparable.
- TSN is Conditional because protein-cycle cash, network optimization, impairments, and Class A/B
  economics remain material.

## Why KMB is withheld

KMB's IFP transaction closed on 2026-07-01, after the reported quarter but before the valuation
date. The filing also reports a still-pending Kenvue acquisition with $6.7B expected cash
consideration and 280M expected shares. Although the filing provides the $1.7B IFP consideration,
disposal-group cash/debt, and H1 revenue, it does not provide one post-IFP, post-Kenvue cash-flow
and capital-structure object. A pre-closing DCF would value the wrong company; a post-closing DCF
would require invented combined cash.

## Challenge and verification

The independent Luna XHigh challenge found and resolved:

- KR finance-lease debt omitted from the first bridge;
- MKC's latest $95M finance lease missing from the current bridge;
- ambiguous HSY lease scope, resolved by the filing's exact debt reconciliation;
- PG preferred conversion, resolved through the disclosed diluted denominator; and
- a reused-packet metadata-wrapper bug that weakened provenance despite identical financial JSON.

Final challenge verdict: **PASS; no remaining Critical or Important findings**.

- Focused Batch 10 tests: `5 passed`.
- Complete backend suite: `1,310 passed, 3 skipped, 1 warning`.
- Frontend production build: passed.
- Real FastAPI: list/detail/calculator parity 10/10; KMB calculator fails closed; private leaks 0.
- Source packet replay hash: `eeabff4deacb2d7ea3279b01f0d20b99f0e1a5d3ea66d834bddfd11365cb4d00`.
- Structural replay hash: `760aa29b4dd0ee101d02494eaea79687fd98cbf488328ba547b205e94645cc4e`.
- Generated replay hash: `ac0467755ebd46616cfee444da8e6c0330cf6f783a704525108b8251d07a5b26`.
- Public replay hash: `6a82f4839b987647f0c96b3aa3aa7f708de66f37c58531d2f53f5a36257539b3`.
- API receipt SHA-256: `ddb4ddaa70046f9b5e0296acbb2b62782cbb2ea286f801dda5d1aa9bbbc245cb`.
- Protected serving hashes and the Recovery Learning Watchlist remained unchanged.

## Confirmation

The user replied `y` and confirmed the initial Batch 10 result on 2026-08-26. MKC, SJM, and TSN
were bookmarked as direct Conditional results. KMB's later authorized recovery is recorded in
Audit 62. Batch 11 requires a later signal.
