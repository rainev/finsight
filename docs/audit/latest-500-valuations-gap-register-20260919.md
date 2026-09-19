# Latest 500 valuation production — gap register

Reference: the user-approved `Refresh All 500 FinSight Companies Through
September 19, 2026` plan and the final SEC snapshot at
`2026-09-19T08:40:23+00:00`.

Status: active gated audit. This register distinguishes evidence freshness,
calculation capability and publication; none is a proxy for another.

## Batch A — universe and historical calculation foundation

- ✔ **Closed:** final SEC submissions metadata covers the exact original
  500 ticker/CIK identities. It identifies 51 changed annual/interim filings
  and 259 companies with event/amendment flags. Source:
  `output/latest-universe-20260919/final-discovery/discovery-report.json`.
- ✔ **Closed:** every one of the 51 changed regular filings has a hash-checked
  captured packet. This proves acquisition, not economic correctness.
- ✔ **Closed:** 474/474 historical numeric valuations have exact executable
  recipes; the 26 prior unavailable companies remain a separate recovery set.
- ✔ **Closed:** an isolated real API exposed 500 details and reproduced every
  historical default calculator from exact recipes with zero sweep errors.
- ✔ **Closed:** BBY's latest calculation was exercised in a fresh isolated
  500-company runtime through activation, worker reload, exact calculator and
  rollback. Production was untouched.
- ✔ **Closed:** isolated PostgreSQL migrations, valuation save/readback,
  user-isolation and cleanup passed; the normal application database was not
  changed.

## Batch B — current valuation candidates

- ✔ **P0:** official updated valuations are not yet a complete successor
  catalog. A source-binding diagnostic does not itself issue or publish a
  catalog version.
- ✔ **P0:** the 51 changed-filings group is being re-run together against the
  final frozen capture. Its current report is the authoritative next gap list;
  older WG and source-validation successes are not added to it.
- ✔ **P0:** BIIB changed after the old review: its official August 6 release
  confirms RayThera closed. The release does not disclose sufficient payment,
  cash, debt or acquired-FCFF reconciliation, so the completed event remains a
  targeted review rather than a numeric input invented from transaction price.
- ✔ **P0:** ADI's post-quarter $3B note issuance and ADSK's post-quarter notes /
  intended term-loan repayment require paired cash/debt reconciliation. Principal
  issued and intended use of proceeds are not automatically net debt.
- ✔ **P0:** AAPL's same-filing diagnostic is a policy/correctness change, not a
  fresh-filing update. Preserve the approved range until its bridge and tax
  changes receive explicit economic approval.
- ✔ **P1:** BBY now has a source-bound candidate using its approved cash-only
  scope, current debt including leases exactly once, current denominator basis
  and a visible $0–$1M NCI reporting-precision bound. Excluded investments are
  outside the model scope, not asserted zero.
- ✔ **P1:** GILD and INCY retain approved annual-only cash-margin exclusions and
  reselect their source-defined YTD/cover share ranges. Their current candidates
  remain subject to final frozen comparison and release integration.

## Batch C — remaining source acquisition and automation

- ✔ **P1:** full supporting-package capture is still running beyond the changed
  group. It was stopped after every changed regular filing was safely captured:
  repeated full structural packages had consumed 3.5 GB while only about 10 GB
  remained. Unchanged/no-event companies now use hash-checked approved evidence
  plus exact recipe replay and final SEC metadata; event/change cases require
  their own captured evidence. Capture failures retain the prior dated estimate
  and are not new economic unavailability.
- ✔ **P1:** 307/474 policies compile. Missing future adapters for an unchanged
  filing do not automatically block retaining an approved baseline, but changed
  filings without mappings require implementation or an explicit review result.
- ✔ **P1:** event item codes alone cannot classify economics. Exact reviewed
  events use accession/document/hash-bound rules; generic item allowlisting is
  prohibited.
- ✔ **P1:** historical inputs from a captured earnings 8-K may be superseded
  only when Item 2.02 is present, all other items are limited to
  7.01/8.01/9.01, the event/report period precedes the controlling regular
  filing, and primary/exhibit relationships are verified. Forward guidance
  remains a limitation, not a reported historical input.
- ✔ **P1:** unchanged-value verification must prove original recipe replay,
  identical controlling evidence, no material post-baseline filing and no
  targeted-review flag. Metadata discovery alone is insufficient.

## Release gate still open

An immutable 500-row successor now exists and has passed isolated API,
calculator, redesigned UI, database, reload and rollback verification. The
historical bridge tranche increased current/checkable numeric estimates from
204 to 227 and reduced historical-only estimates from 270 to 247. The release
gate remains open because 150 acquisition/capture gaps, 74 event reviews,
13 changed-financial source updates and 10 targeted reviews remain explicit.
Production activation, scheduling, merge, push and deployment remain out of
scope.
