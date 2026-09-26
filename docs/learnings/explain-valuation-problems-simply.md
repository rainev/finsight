---
name: explain-valuation-problems-simply
description: Explain every FinSight valuation problem in grade-school-level plain language before technical details.
metadata: { type: feedback }
---
When a FinSight valuation problem appears, explain it in simple language before using technical terms. For each problem, state: **what is wrong, why it matters, the recommended fix, and what happens if it is not fixed**. Clearly distinguish “we lack trustworthy data” from “we have data, but the valuation method is weak.”

**Why:** The user cannot make an informed product decision or prompt for the right solution when the explanation is too technical.

**How to detect / apply:** If the explanation contains accounting jargon, acronyms, or pipeline terminology, add a plain-language translation. Use a small example when useful. Ask only for decisions the user genuinely needs to make. Whenever reporting a count, explicitly say “X out of Y, selected because Z.” Never call a limited test batch the “full corpus” without naming the universe it is full for. Never say something merely “passed”: name the exact gate, such as parser opened the filing, accounting fields mapped, valuation calculated, or publication approved.
