---
name: typed-dimension-without-value-cannot-classify-financing
description: A typed-axis marker without its typed member value cannot distinguish operating accounts payable from financing.
metadata: { type: gotcha }
---
KDP reports two supplier-finance location components that sum to the total, but
the structural packet retains each location only as `typed`. The filing narrative
identifies one amount as accounts payable and the other as structured financing,
yet matching those meanings back by amount would be reverse-fitting. **Why:** a
numeric reconciliation proves completeness, not semantic identity. **How to
detect / apply:** preserve typed member values during structural parsing and bind
location meaning from that source identity; until then, retain all values and
return review rather than selecting the financing component by magnitude.

WG10 fixed the loss by adding `typed_dimensions` as a backward-compatible
axis/domain/value triple while keeping legacy `dimensions` marked `typed`. Old
artifacts remain readable; a current-parser immutable reparse is required before
semantic binding. KDP then resolves accounts payable versus structured financing
directly from `AccountsPayableCurrent` and `StructuredPayablesCurrent`.
