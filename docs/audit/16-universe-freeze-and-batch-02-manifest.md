# Frozen replacement universe and Batch 02 manifest

**Audited:** 2026-08-24 (Asia/Manila)

**Scope:** freeze the user-authorized replacement 500-issuer universe and all remaining batch
assignments; disclose the exact Batch 02 ten before any company processing

**Status:** verified — user confirmation needed; Batch 02 is frozen but unprocessed

## Authorized universe

The original historical 500-row artifact was not recoverable. After the hard stop recorded in
Audit 15, the user explicitly authorized an S&P 500 issuer universe effective 2026-08-14 as the
replacement reset denominator.

The reproducible public reconstruction uses:

- the pinned Wikipedia constituent revision `1369213082`, timestamped
  `2026-08-13T15:09:18Z`;
- the official S&P announcement that RDDT would replace AVB before the 2026-08-18 market open,
  which corroborates AVB-in/RDDT-out at the 2026-08-14 cutoff; and
- a captured SEC company-ticker mapping for CIK reconciliation.

This is honestly classified as a **public reconstruction**, not a licensed historical S&P
constituent export. The source table has 503 securities representing exactly 500 unique issuer
CIKs. The three duplicate-CIK share-class groups are frozen as NWSA for News Corp, GOOGL for
Alphabet, and FOXA for Fox. The cutoff EQR identity is preserved as CIK `0000906107`; the
post-cutoff VMRK plan and current SEC-map drift are recorded as corroboration, not rewritten as a
cutoff membership change.

Sources:

- `https://en.wikipedia.org/w/index.php?title=List_of_S%26P_500_companies&oldid=1369213082`
- `https://press.spglobal.com/2026-08-13-Reddit-Set-to-Join-S-P-500-and-Sun-Communities-to-Join-S-P-MidCap-400`
- `https://www.sec.gov/files/company_tickers.json`

## Source and determinism receipt

- Canonical universe version: `US-SP500-ISSUERS-2026-08-14-1.0`.
- Canonical universe SHA-256:
  `cc11df21ee64c5e6ff6cc49fb20f7dbb7b05f1f23b7eea6acea4b190720e8a8b`.
- Constituents HTML SHA-256:
  `02be4d0442788ccfbac9dfb5b24f34007baf44586e215a2c6ab4001b99b000f9`.
- Revision metadata SHA-256:
  `866e804d4403ec477e693b3ee55195406cb1f6fe0ead40664dbabd5ee04fc845`.
- SEC mapping SHA-256:
  `0f91b08800b52003ab0731fd40cd5ae498aaf7805a7290f75501cf965cbd24bd`.
- Normalized S&P change evidence SHA-256:
  `d2a9b41fa3bec5167634c0c2b345bf3d6c782b2252047e30d67797266b20c00d`.

Two fresh source captures had different raw S&P page bytes but produced byte-identical canonical
universe files. Raw bytes and their per-run hashes remain preserved; only the normalized economic
event drives canonical identity.

## Frozen partition

The locked Batch 01 ten remain unchanged and are explicitly grandfathered from the future-batch
composition constraint. The remaining 490 unique CIKs are assigned exactly once to Batches
02–50:

- `10 + 490 = 500`, with no omissions or duplicates;
- exactly 49 future batches of ten;
- every future batch has eight core and two predeclared boundary companies;
- 44 batches have one partition cohort family and five have two; none exceeds two;
- no valuation result, publication state, reliability, source availability, intrinsic value, or
  processing cost is used in selection; and
- `partition_family_id` is a workload/preflight grouping only. Final source-backed model routing
  remains a separate decision and cannot change batch membership.

The initial mechanically valid partition was rejected because its boundary companies were
leftovers with false lane metadata. The corrected partition keeps each issuer's actual sector
lane. Most boundaries are rare subindustries within their cohort; the 13 cross-sector exceptions
have named economic reasons.

Two independent fresh freezes match the stored manifests byte for byte. Partition version
`US-RESET-PARTITION-2026-08-14-2.0` has root SHA-256
`fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`.

## Exact Batch 02

| Role | Ticker | CIK | Issuer | Subindustry |
| --- | --- | --- | --- | --- |
| Core | OMC | 0000029989 | Omnicom Group | Advertising |
| Core | VZ | 0000732712 | Verizon | Integrated Telecommunication Services |
| Core | T | 0000732717 | AT&T | Integrated Telecommunication Services |
| Boundary | TTWO | 0000946581 | Take-Two Interactive | Interactive Home Entertainment |
| Core | NFLX | 0001065280 | Netflix | Movies & Entertainment |
| Core | CHTR | 0001091667 | Charter Communications | Cable & Satellite |
| Core | CMCSA | 0001166691 | Comcast | Cable & Satellite |
| Core | TMUS | 0001283699 | T-Mobile US | Wireless Telecommunication Services |
| Core | META | 0001326801 | Meta Platforms | Interactive Media & Services |
| Boundary | WBD | 0001437107 | Warner Bros. Discovery | Broadcasting |

All ten are Communication Services issuers. TTWO and WBD are predeclared same-cohort rare-
subindustry boundary cases. Batch 02 manifest SHA-256 is
`b2087a061ddbabf48a2adca8df7f56997503706207150e3017f0425de7f473a7`.

## Independent challenge and stop boundary

A provenance-focused review passed the 500-issuer reconstruction, cutoff handling, share-class
policy, EQR exception, and canonical determinism. A separate adversarial partition review passed
the exact cover, role/lane semantics, 20 shuffled-input builds, two fresh freezes, and stored
hashes with no remaining Critical or Important finding.

## Final firsthand verification

The cached real-source reconstruction was exercised again through `build_universe`. Observed
result:

```json
{"avb_present": true, "byte_equal": true, "issuer_count": 500, "multi_class_primaries": {"0001564708": "NWSA", "0001652044": "GOOGL", "0001754301": "FOXA"}, "rddt_absent": true, "security_count": 503, "sha256": "cc11df21ee64c5e6ff6cc49fb20f7dbb7b05f1f23b7eea6acea4b190720e8a8b", "unique_ciks": 500}
```

Runs D/E had unequal raw S&P-notice hashes (`45ab4690…` versus `371b3e49…`) but identical
canonical-universe hashes (`cc11df21…`) and byte-for-byte equality.

Fresh real-artifact freeze command:

```text
python3 scripts/freeze_universe_batches.py \
  --output-root output/universe-reset/partition-verification-run \
  --config-root output/universe-reset/partition-verification-config-mirror
```

Observed result:

```json
{"batch_02_tickers": ["OMC", "VZ", "T", "TTWO", "NFLX", "CHTR", "CMCSA", "TMUS", "META", "WBD"], "future_batch_count": 49, "future_issuer_count": 490, "partition_root_sha256": "fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4"}
```

Both fresh output roots compare byte-for-byte with the stored configuration. Complete backend
suite: `1089 passed, 3 skipped, 1 existing deprecation warning`. Serving JSON aggregate hash
before and after verification: identical
`8b8f3e1bd6783b43d658253c6b04d71c13ea693df63a4bebe402aac514f87cac`.

No Batch 02 SEC packet, economic profile, valuation, publication result, recovery attempt,
serving write, promotion, Batch 03 work, merge, or deployment is authorized by this freeze. The
next signal is **`Process frozen Batch 02.`** That signal starts only the initial Batch 02 pass and
must stop after reporting every numeric and withheld result.
