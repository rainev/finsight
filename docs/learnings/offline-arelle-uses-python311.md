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
