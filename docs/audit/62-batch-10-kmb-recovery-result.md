# Batch 10 KMB Recovery Result

Status: **user confirmed on 2026-08-26**. The user authorized KMB's one recovery attempt.
No serving promotion, Batch 11, merge, push, or deployment was performed.

## Outcome

- Pass: **6/10** — HSY, HRL, KR, PEP, PG, WMT
- Conditional: **4/10** — KMB, MKC, SJM, TSN
- Withheld: **0/10**
- Numeric: **10/10**

KMB is recovered as a **Conditional Low current-state estimate**:

| Low | Base | High | Economic state |
| ---: | ---: | ---: | --- |
| $15.88 | $36.32 | $61.27 | Post-IFP closing, pre-Kenvue closing |

## Recovery model

The controlling 2026-06-30 filing reports the IFP transaction closed on 2026-07-01 for
approximately $1.3B cash, with KMB retaining a 49% stake initially valued near $1.2B. Transferred
IFP debt is non-recourse to KMB. The pending Kenvue acquisition—$6.7B expected cash and roughly
280M expected shares—is deliberately excluded and is not probability-weighted.

Because consolidated OCF contains discontinued working capital, it is diagnostic only. Continuing
cash is proxied from reported H1 continuing EBIT, D&A, and continuing capex:

`2 × (continuing EBIT × (1 − tax) + D&A − continuing capex)`

The model uses reported continuing H1 revenue of $8.352B versus $8.217B prior-year, $956M remaining
cash, $6.517B remaining debt/capital leases, $124M NCI, $22M redeemable claims, and 333.3M diluted
shares. The bear case retains the separately reported $81M IFP capex as a transition reserve.

The reported approximate sale cash and retained-stake value receive a 10% bear reserve for closing
adjustments, tax, and valuation uncertainty. The preliminary gain is not added separately because
cash proceeds and retained-stake fair value already represent the transaction.

## Why it remains Conditional

- standalone continuing working-capital cash is not separately reported;
- post-closing IFP adjustments can change the approximate cash/stake values; and
- Kenvue may close, terminate, or change financing, producing a different company and denominator.

Any Kenvue state change invalidates this current-state range.

## Challenge and verification

The independent source audit established the post-IFP balance sheet, continuing operating inputs,
IFP cash/stake values, and Kenvue terms. The independent Luna XHigh challenge found and resolved:

- consolidated OCF initially mixed discontinued working capital;
- an unsupported five-year-history label;
- an undisclosed $81M bear transition-capex reserve; and
- stale public wording that still described KMB as unavailable/history-backed.

Final challenge verdict: **PASS; no remaining Critical or Important findings**.

- Focused Batch 10/recovery tests: `8 passed`.
- Complete backend suite: `1,313 passed, 3 skipped, 1 warning`.
- Real FastAPI: list/detail/calculator parity 10/10; KMB calculator enabled; private leaks 0.
- Recovery candidates are byte-identical.
- Generated replay hash: `78e47dfa037b2cc8dd9467278a208e227590ebe4f260c900ea142694dba7fa3a`.
- Public replay hash: `2ea914a40a9d1d937a904c9514a153c9fae6b731506e14b0534ab89bb2e503de`.
- API receipt SHA-256: `a5253c7c84dab59242797540007417ee5f1d1737c6014076475444df602c2e74`.
- Serving artifacts remained unchanged.
- KMB was added to the Recovery Learning Watchlist as Conditional; the cumulative withheld
  register was not changed.

## Confirmation

The user replied `y` and confirmed the KMB recovery on 2026-08-26. Final Batch 10 is Pass 6 /
Conditional 4 / Withheld 0. Batch 11 requires a separate user signal.
