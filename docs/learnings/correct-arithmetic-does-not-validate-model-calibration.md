---
name: correct-arithmetic-does-not-validate-model-calibration
description: A valuation can reconcile every source and formula yet remain economically off when generic caps sever the model from issuer evidence.
metadata: { type: feedback }
---
Treat source/mechanical correctness and model calibration as separate release gates. Batch 12's
initial values had exact sources, periods, bridges, TTM arithmetic, and monotonic scenarios, but a
blanket five-year DCF capped every issuer at 3%/4%/5% growth and used fixed 0%/1%/2% terminal
growth. That was especially misleading for LLY, whose source-linked historical median growth was
25.78% and current H1 growth was 51.2%, and for HUM/CVS, whose fixed earnings multiples ignored
reported common equity and ROE.

**Why:** passing source and arithmetic checks proves the model computed its policy correctly; it
does not prove the policy is a useful representation of the issuer. The user correctly flagged
that many values looked off even after the mechanical audit passed.

**How to detect / apply:** always compare governed growth, fade, terminal, required-return, and
multiple assumptions to current and historical issuer evidence. Record large policy haircuts
explicitly, use an issuer-suitable model (such as residual income for insurer equity), and run an
independent economic-usefulness lens after the source/mechanics lens. Never price-fit to market.
Related: [[baseline-decision-is-not-market-prediction]] and
[[public-competitor-methods-are-constraints-not-formulas]].
