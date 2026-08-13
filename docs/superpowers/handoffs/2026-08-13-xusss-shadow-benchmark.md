# XUSSS/XULE shadow benchmark handoff

Date: 2026-08-13 (Asia/Manila)

Status: **verified — public 2024 normalizer rejected for FinSight's current filings**.

## Resume location

- Worktree: `/Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution`
- Branch: `feat/structural-xbrl-resolution`
- Durable evidence: `docs/plans/EVIDENCE.md` under “XBRL US XUSSS/XULE public-normalizer shadow benchmark”
- Raw shadow outputs: `output/structural-xbrl-xusss-benchmark-20260813/results/`
- Learning: `docs/learnings/xusss-public-normalizer-is-taxonomy-version-bound.md`

Use FinSight Efficiency Mode and GoodBehavior. Do not rerun Tasks 1–4 or repeat this public
2024-rule benchmark unless XBRL US publishes a taxonomy-year-matched rule bundle.

## Verified result

- Reproduced the official notebook environment in a disposable venv: Arelle 2.36.4, XULE
  30044, EDGAR 25.0.1, and `aniso8601` 9.0.1.
- Ran DE, APD, MO, ORCL, LRCX, KR, T, EXPE, NVDA, and A from their immutable local SEC packages.
- 10/10 generated valid XBRL-JSON offline with no successful-run log errors.
- The ten filings had 51 missing bridge requests; XUSSS recovered 0.
- All ten produced only 29 financial facts across two concepts. Nine emitted only
  `OtherAssetsNoncurrent`; KR also emitted `LongTermDebtNoncurrent`.
- The exact official 2024 positive control produced 237 standardized financial facts across
  118 concepts, proving the setup works for the rule set's intended taxonomy year.
- APD and KR supplied independently reproduced unsafe mappings. See `EVIDENCE.md` for exact
  values and source reconciliation.
- No production code, dependency pin, valuation input, serving artifact, or publication gate changed.

## Architecture decision

Keep:

- Arelle for full XBRL/Inline-XBRL parsing and structural evidence.
- FinSight's deterministic resolver and fail-closed accounting gates.
- XUSSS only as a possible canonical vocabulary/reference.
- XULE only as an optional engine for rules that FinSight owns or that exactly match the filing
  taxonomy year and pass a precision-first benchmark.

Reject:

- The public `2024-ugt-norm.zip` bundle as a fallback for 2025/2026 filings.
- Any normalized amount that cannot be traced to the original concept, context, dimensions,
  period, unit, statement role, and accounting reconciliation.
- A full-universe replay of the same stale bundle.

## Recommended next action

Return to the FinSight-owned resolver. Rank the 545 current decisions by recurring reason code
and economic field, then implement only high-frequency deterministic rules with source-level
tests. Start with cases where Arelle already exposes exact carrying-amount evidence; leave
commercial paper, combined debt-and-lease totals, disclosure schedules, and ambiguous extensions
at review/reject until accounting structure proves the classification.

If a newer external normalizer is proposed, first require a five-company taxonomy-matched
precision gate plus one official positive control. One unsafe promotion rejects the candidate.

## Copy-paste continuation prompt

```text
Resume FinSight structural XBRL work from the verified XUSSS benchmark handoff.

Worktree: /Users/carlosconda/Desktop/Investing Application/.worktrees/structural-xbrl-resolution
Branch: feat/structural-xbrl-resolution
Handoff: docs/superpowers/handoffs/2026-08-13-xusss-shadow-benchmark.md
Evidence: docs/plans/EVIDENCE.md

Use FinSight Efficiency Mode and GoodBehavior. Do not redo Tasks 1–4 and do not integrate or
rerun the public 2024 XUSSS rules on 2025/2026 filings. Resume with the FinSight-owned Arelle
resolver: rank recurring unresolved/rejected bridge fields, choose the highest-value deterministic
accounting rule, implement it with provenance-preserving tests, and rerun shadow eligibility.
Keep all production valuation inputs and publication gates unchanged until the zero-unsafe gate passes.
```
