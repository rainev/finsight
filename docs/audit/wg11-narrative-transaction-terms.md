# WG11 narrative transaction terms and fixed-payment schedules

Verified 2026-09-09; user confirmation pending. This is a bounded working-group
result, not release approval. Production, scheduling, merge, push, deployment,
later batches and family adapters were untouched.

## What changed

`FINSIGHT-NARRATIVE-EVIDENCE-WG11-1` is a deterministic private extraction
layer over the primary filing declared by a hashed SEC package. It uses the
standard-library HTML parser, excludes hidden/script/style content, normalizes
visible text, requires one versioned section, and extracts exact terms with
document, section, normalized-text locator, value, unit/date, excerpt hash,
package hash and extraction-version provenance. It uses no AI or OCR.

Receipts are re-extracted from the frozen raw bytes before use. The live refresh
capture attaches the same receipt from the newly cached filing package. Frozen
two-worker verification hashes the receipt, package manifest and raw primary
document, and rechecks external bytes after worker execution.

## Company results

| Company | Result | Previous low / base / high | Current low / base / high |
|---|---|---|---|
| MCHP | Source-bound representative | 3.0508679571950985 / 17.758157215797535 / 46.424128171930924 | 3.04622665282325 / 17.643659016284587 / 45.8291380000971 |
| BMY | Difficult source/economic review | 39.97686970283852 / 69.48694725602633 / 108.19648925209388 | No candidate; prior dated estimate retained |

MCHP changes are -0.004641304371848509 / -0.11449819951294771 /
-0.5949901718338211 per share (-0.1521% / -0.6448% / -1.2816%). The
new exact-date dividend PV is $177,575,903.30296987 / $179,524,076.4248368 /
$180,854,280.54929465. The scenario conversion shares are 29,117,880 /
26,443,395 / 23,768,910. The current source dilution proxy is locked at
550,308,691 before preferred conversion, rather than preserving the legacy
scenario-specific 550,500,000 / 546,754,345.5 / 543,008,691 assumptions. The
$1.485B liquidation preference is not deducted with conversion dilution, and
the $71.40 capped-call surface remains excluded because its realized benefit is
not source-bound.

BMY's current structured/narrative evidence supports $607M of recognized Mirati
CVR liability plus $950M of Hengrui fixed payments. It also proves that $1.5B of
BioNTech cash was already paid, while $2.0B of future BioNTech anniversary
payments is disclosed only as a Q3-2026-through-2028 envelope. The $14.3B
Hengrui and $7.6B BioNTech milestone maxima remain non-liability event surfaces.
Because the $2.0B fixed envelope lacks an exact annual allocation, the pipeline
does not invent a payment schedule or issue a new BMY value.

## Verification evidence

- MCHP narrative receipt:
  `output/us-refresh-runtime/narrative-evidence/MCHP.json`, receipt
  `b1ae72f39e83bad6730dd69a4574ea5fa30fdb2373b402f9862d1c9473386dc7`,
  raw filing `43bc8ef18e558929d6bb289ce345827f40edc5cdacf81379265071c333a69ad6`.
- BMY narrative receipt:
  `output/us-refresh-runtime/narrative-evidence/BMY.json`, receipt
  `5620a4cd241b5a1df3b027cdb2fb06e2d677d33d988ddbb981b9bd18d0aa84f6`,
  raw filing `324737170e9f9c3066c22abeb95134f6e2d4f94a974aa69903b616c0283af168`.
- Frozen two-worker group:
  `output/us-refresh-group-verification/f79130cf67de81fc976f9229a4ce5d83c442312b7974429f381c2dad366b4b60/report.json`,
  file SHA-256 `99fbedbd5649015a2122404cdcfd1eebc945da846d8f9ca23e7bb822d497631f`.
  Outcome: one cached source-bound candidate and one explicit review.
- Direct source evidence:
  `output/us-refresh-runtime/source-validation/63c9d38a858bbc35f40e777a39ad99ff93898c2b50c51895f8f7c8fadc297692/report.json`.
- Focused regression: 120 passed; one unrelated dependency deprecation warning.
- Isolated MCHP API/database UAT:
  `output/us-refresh-operational-uat-20260909T145019Z-8e3be4dc/uat-report.json`,
  SHA-256 `39a19182459110845459d9149d811546ad01fae25b7e4128d177bcd8ccb7757c`.
  A real FastAPI worker served the old and new ranges, pinned and reloaded one
  catalog version per request, rejected stale CAS, preserved 440 registry rows
  and 419 recipes, then rolled back. Production was not touched.
- Current work register: `output/us-refresh-work-register.json`, SHA-256
  `d45ba1fcd6c0dc96785fba40d0f66649d860ce91bf70dd25ac2002cff891d9bd`.
  Counts are 259 compiled contracts, 160 implementation gaps, one current-policy
  source-bound result, 159 source gaps, 188 financial reviews and zero explicit
  successive-period proofs.

## Remaining blockers

- BMY needs source-supported allocation or exact dates for the $2.0B BioNTech
  fixed-payment envelope, plus cutoff-safe evidence of any payment already
  made. Until then its previous dated range remains history, not a new result.
- MCHP is verified only for the current filing/cutoff. A later real filing must
  still pass the same parser and calculation to count as successive-period
  verification.
- WG11 does not prove full-universe readiness; 160 implementation gaps and the
  final release gates remain.
