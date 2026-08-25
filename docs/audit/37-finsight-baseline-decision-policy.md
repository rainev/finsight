# FinSight Baseline Decision Policy

**User decision:** FinSight should estimate where the road goes and drive slowly. Its purpose is to
give users a useful baseline for thinking, not to claim it can predict or beat the market.

## Default behavior

After the hard data-safety gate passes, produce a value range even when future economics require
judgment:

- use reported TTM performance and longer annual history;
- use simple company/industry-normalized cash, margin, reinvestment, growth, and risk assumptions;
- construct coherent bear, base, and bull states;
- disclose a short warning and keep the complete assumption/source ledger privately;
- cap material assumption-driven results at Low reliability;
- label them conditional when the range depends on an event, transaction, major product launch,
  incomplete capital allocation, or another non-reported future state;
- add every material conditional result to the Recovery Learning Watchlist.

FinSight is producing a decision-support baseline, not a price target, buy/sell recommendation,
probability-weighted market forecast, or promise of excess returns.

## Withhold only for hard failures

Withholding is reserved for:

- wrong or unreliable issuer/source/period/unit/currency;
- an unreliable share denominator;
- materially contradictory evidence;
- no economically coherent valuation object or model;
- every reasonable scenario producing unusable/nonfinite residual equity;
- a public-safety failure.

Missing perfect detail, uncertain commitments, pending transactions, short history, weak
predictability, or specialist-model incompleteness are not sufficient by themselves. They widen the
range, lower reliability, change the model label, and trigger the watchlist.

## Batch workflow

- Batch 03 remains paused at its already-reported initial source-bounded result. Its separately
  signaled recovery will apply this baseline policy to the seven holdouts.
- Beginning with Batch 04, the normal initial batch pass includes the baseline conditional layer
  after hard safety checks, so ordinary uncertainty does not create an unnecessary withheld queue.
- The existing one-recovery workflow remains available for genuine hard failures or challenged
  estimates.

## Guardrail

“Give a baseline” does not mean inventing hidden facts. Estimated inputs must be explicitly marked,
directionally sensible, internally consistent, and broad enough to acknowledge what is unknown.

