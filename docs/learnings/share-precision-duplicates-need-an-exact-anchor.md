---
name: share-precision-duplicates-need-an-exact-anchor
description: APO, BLK, FITB, IBM and SNA report exact and rounded duplicate diluted-share presentations under the same source scope.
metadata: { type: gotcha }
---
Residual refresh corroboration compared every structural share presentation with
CompanyFacts using exact equality. Five real filings had a whole-share figure
and an explicitly rounded sibling, creating false conflicts. For example APO
reports 593,298,193 and 593,300,000 with decimals 0 and -5 for the same H1 context.

Require a unique precise structural anchor corroborated exactly by CompanyFacts.
Every sibling must match issuer, accession, QName, period, dimensions and share
units, and its declared XBRL precision interval must contain the anchor. Reject
unknown CompanyFacts values and contradictory precise facts. Retain all reported
presentations in private evidence; select the anchor only in the normalized copy.
Do not change period selection or apply an arbitrary percentage tolerance.

Version the rule so older frozen policy behavior remains distinguishable. Source
checks now bind APO/FITB/SNA; BLK's preferred claim and IBM's common-equity proof
remain separate blockers. This correction does not validate their whole models.
