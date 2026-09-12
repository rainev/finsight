---
name: offline-arelle-uses-python311
description: Run FinSight structural filing ingestion with Python 3.11 because the default Python runtime does not contain the pinned Arelle dependency.
metadata: { type: gotcha }
---
FinSight's pinned `arelle-release==2.44.0` ingestion dependency is installed for the
`python3.11` runtime. The default `python` runtime can capture an SEC filing package but then
fails at structural parsing with `ArelleUnavailable: No module named 'arelle'`.

**Why:** package capture and structural parsing occur in separate steps, so using the wrong
interpreter can leave a valid partial package cache while producing no accepted structural
output.

**How to detect / apply:** confirm `python3.11 -m pip show arelle-release` before a structural
run and invoke structural capture with `python3.11`. Preserve and reuse any complete package
cache left by a failed wrong-interpreter attempt; write the corrected structural replay to a
new immutable output root.

Large filings can also exhaust the worker's default 120-second CPU allowance even when the
package and interpreter are correct. Keep 120 seconds as the safe default, but for an identified
large controlling filing rerun structural capture with a bounded process-level override such as
`FINSIGHT_ARELLE_CPU_LIMIT_SECONDS=240` and a matching caller timeout. Record the override in the
capture evidence; never raise the serving-process limit or silently treat a CPU-limit exit as
missing filing data.

Verified on 2026-09-08: some early structural-shadow JSON files predate fact-level
`entity_identifier`. Do not add the issuer CIK to those old facts by assumption;
reparse the retained raw package with the current worker. Apple's cached 10-Q
then yielded 716 facts, all with issuer CIK `0000320193`. Its top-level parser
period remained the July 17 cover-share date; the balance-sheet facts themselves
remain June 27. Continue selecting exact fact contexts, not the top-level period.

The refresh parsed-cache check must run **before** invoking Arelle. A cache-hit
flag in the receipt alone did not prove that parsing was skipped. The corrected
lazy loader was exercised against ADP's real raw package: one parser invocation
for two captures at successive cutoffs, with unchanged normalized source content.
