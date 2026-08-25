# Batch 02 revised-pipeline recovery retry result

**Valuation date:** 2026-08-14

**Authorization:** explicit user-requested retry after the official-evidence pipeline revision.
This is recorded separately from the one automatic recovery attempt in Audit 18.

## Exact outcome

- Retry denominator: **6/6** — OMC, TTWO, CHTR, CMCSA, META, WBD.
- Newly numeric: **0/6**.
- Still withheld: **6/6**.
- Final Batch 02: **4/10 numeric Low, 6/10 withheld**.
- Invalid/skipped/replaced: **0/10**.
- Public artifacts changed: **0/10**.
- Serving artifacts changed: **no**.

## What the revised pipeline improved

| Ticker | Governed reported/bounded fields | Unresolved requests | Why publication is still withheld |
| --- | ---: | ---: | --- |
| OMC | 5 | 11 | Current bridge facts do not supply comparable combined OMC-plus-IPG owner-cash history. |
| TTWO | 5 | 11 | Current bridge facts do not bound GTA-VI release conversion or supply post-release cash evidence. |
| CHTR | 5 | 11 | Standalone current claims do not bound combined Cox/Liberty cash flow, final leverage, or dilution. |
| CMCSA | 6 | 10 | Consolidated facts do not supply post-separation cash flows, corporate-cost allocation, or final financing allocation. |
| META | 6 | 10 | Lease ranges do not reconcile overlap among commitments, uncommenced leases, and future capex. |
| WBD | 8 | 8 | Current bridge facts do not create a finite standalone/separation state; conditional merger cash is not intrinsic value. |

The 35 selected/bounded fields were checked against cutoff-eligible attempts; all were filed on or
before 2026-08-14. Explicit reported zero remained distinct from unavailable data, and bounded
ranges remained ranges.

## Real-consumer challenge

The FOD5 real valuation replay contains exactly the six retry issuers. Every case:

- replayed successfully with a private evidence trace;
- consumed exactly its projected evidence count with zero unused/mismatched projections;
- remained `withheld` and nonnumeric;
- produced no public schema change or unsafe promotion.

This independently confirms that the outcome is not a missing wiring step: the revised evidence
reached the real valuation consumer, but did not clear the economic release conditions.

## Determinism and regression evidence

- Official policy A/B input SHA-256: `fbd65c1c30d8dfbaeb8a136f410f2004f950af4c2b1f3a92d652950efa07d1e4`.
- Full replay SHA-256: `d586fe8696f98b96fdb1c851d17cb9272ee4dd78195bb7a1a2601de73a3d60c3`.
- Prior recovery report SHA-256: `00cb240eeaadc1351b8312c29c9d9cbab13368a285981fb0dac56f05ddb61d20`.
- Retry report SHA-256: `2af21476f637a138da1c74e5f1dfe6807ea6b8bf46ad038bf6092a83b6672fbf`.
- Two complete retry trees are byte-identical: `b201d3359f9d9cdf13ff4a6b4f523e3ae9f2f540e3906a93e76994e3e18abe45`.
- Focused retry/register tests: **6 passed**.
- Complete backend suite: **1,181 passed, 3 skipped, 1 warning**.
- `git diff --check`: passed.

## Real API verification

The actual FastAPI app served the ten staged Batch 02 public artifacts on localhost port 8765:

- list: HTTP 200, exact count 10, exact staged parity;
- details: 10/10 HTTP 200 and exact staged parity;
- private leaks: 0;
- forbidden Arelle/official-ingestion/specialist serving imports: 0.

Receipt: `output/batch-02-revision-retry/api-verification-20260824.json`, SHA-256
`0ed55d930c54353b0aa759fb80a2a1a80a80b2fc6641d9c0779f97f9f306a465`.

## Governance result

The six companies retain `recovery_attempts: 1`. Their explicit user-authorized pipeline revision
retry is recorded separately as `pipeline_revision_retries: 1`; the automatic retry allowance was
not reset. They remain in the cumulative universe-reset withheld register.

**Gate:** verified technically; user confirmation is still required. Stop before Batch 03, merge,
deployment, promotion, or serving-data modification.

