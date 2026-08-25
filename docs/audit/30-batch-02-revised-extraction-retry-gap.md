# Batch 02 revised-extraction recovery retry gap audit

**Valuation date:** 2026-08-14

**Scope:** the six Batch 02 issuers still withheld after the single automatic recovery:
OMC, TTWO, CHTR, CMCSA, META, and WBD.

**Authorization:** the user explicitly requested one retry after the official-evidence pipeline
revision. This is a separately recorded revision retry; it does not reset or increase the
one-automatic-recovery allowance in Audit 18.

## References re-read

- `docs/audit/18-batch-02-recovery-result.md` — prior recovery decisions and issuer-specific
  release conditions.
- `output/fod5-policy-batch02-a.json` and `-b.json` — byte-identical governed evidence decisions
  for all ten Batch 02 issuers.
- `output/fod5-full-replay-g/full-replay-report.json` — real valuation-consumer replay with private
  trace, exact projection consumption, public-boundary checks, and unchanged serving roots.
- `output/batch-02-recovery/verified-run-a` — immutable starting private/public recovery artifacts.

## Reuse audit

No new crawler, parser, valuation engine, or competitor formula is needed. The smallest valid
implementation is a deterministic receipt that joins the existing recovery decisions to the new
official-evidence policy and real-consumer replay, re-evaluates the named release conditions, and
keeps the public artifacts byte-identical unless a blocker is actually cleared.

## Gaps

| ID | Severity | Issuer | Revised evidence now available | Remaining material gap | Classification |
| --- | --- | --- | --- | --- | --- |
| RX-01 | P0 | OMC | Current cash, debt, NCI, and a bounded lease aggregate | No comparable combined OMC-plus-IPG owner-cash history or issuer-filed combined pro forma cash flow | Major event / model gap remains unbounded |
| RX-02 | P0 | TTWO | Current cash, debt, and marketable securities | No source-backed GTA-VI release conversion range or post-release cash observation; normalized cash remains nonpositive/unbounded | Major event / model gap remains unbounded |
| RX-03 | P0 | CHTR | Current cash, debt, NCI, and preferred-equity zero | No combined Cox/Liberty operating cash, final leverage, conversion dilution, or complete claims state | Major event / claims gap remains unbounded |
| RX-04 | P0 | CMCSA | Current cash, current debt, securities, NCI, and preferred-equity zero | No standalone post-separation cash flows, corporate-cost allocation, or final debt/cash/financing allocation | Major event / model gap remains unbounded |
| RX-05 | P0 | META | Cash, securities, debt, and bounded finance-lease ranges | No mutually exclusive cash waterfall for the $349.31bn commitments and $278.99bn uncommenced leases; overlap with capex remains unresolved | Claims / model gap remains unbounded |
| RX-06 | P0 | WBD | Current cash, debt, NCI, preferred-equity zero, and bounded lease ranges | Conditional merger consideration is not intrinsic value; no finite standalone/separation terminal state | Major event / model gap remains unbounded |
| RX-07 | P1 | Register | Six issuers already have `recovery_attempts: 1` | The explicit revision retry must be recorded separately without weakening the one-automatic-attempt invariant | Governance/trace gap |

## Gate

The retry may proceed only if it:

1. validates the exact six-company denominator and the two frozen official-evidence inputs;
2. proves every evidence projection was consumed by the real valuation consumer without mismatch;
3. records which newly extracted fields changed the evidence picture and whether the prior economic
   blocker was cleared;
4. writes only immutable untracked evidence, keeps all ten public artifacts byte-identical, and
   leaves protected serving roots unchanged;
5. reproduces byte-identically twice, passes focused and full backend tests, and passes real local
   API list/detail/privacy/import checks;
6. records the explicit revision retry separately in the cumulative register and stops before
   Batch 03.

**Pre-build finding:** extraction coverage improved, but no revised evidence currently clears any
of the six issuer-specific economic release conditions. That claim remains unverified until the
deterministic retry and real-consumer/API gates complete.
