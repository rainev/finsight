# FinSight US700 source and data handoff

Prepared 2026-10-16 for review in `rainev/finsight`, based on PSE commit
`42d62f4d92db0b3452316d779787f034f601f69a`. This is a review branch, not a merge,
hosted release, SEC refresh, partner activation or backend-repository migration.

## What changed since the previous 500-company handoff

- The approved local universe contains **700 companies**, **574 numerical public
  estimates** (104 available + 470 conditional) and **126 unavailable**.
- There are **200 additions since 500**. The most recent 50 are expansion
  Batches16–20, catalog batches66–70. Only MMS and FCN have numerical public
  estimates among those50; the other48 remain public-null. Private LSTR and
  earnings-pricing alternatives are not included in the public company list.
- `us700-companies.json` contains the full derived list, including dates,
  reliability and warnings. `added_since_500` identifies all200 additions;
  `expansion_batch`16–20 identifies the latest50. Missing values remain null.
- Latest50 evidence cutoff: **2026-10-13**. Usable numerical AlphaSpread
  comparisons: **0/50**. Economic calibration/closeness is not established.
- The exact catalog identity, artifact hashes and private-package digest are
  pinned in `us700-receipt.json`. Existing values, dated scopes, Low warnings,
  public nulls and new-filing holds are retained, not recalculated for transport.

## What is in this branch

1. MAIN U.S. valuation source, models, router, calculator, inheritance and runtime
   worker/control implementation, with US-only shared application/frontend wiring.
2. `us_refresh_parser/`: the separate source-bound parser/runner implementation
   from the US worktree. Keeping it separate avoids silently choosing between
   diverged MAIN/PSE-side and US-worktree implementations. Original branch commits
   remain unchanged. This is not a claim that every historical divergence has
   been adjudicated or that branch-wide tests are portable.
3. A private archive staging command and isolated HTTP/offline-worker verifiers.
4. The public700 list and receipt. These are handoff records, **not** a serving
   manifest, source-financial dataset, calculator recipe or active pointer.

The US control still depends on the shared PSE refresh-control identity fields
and Friday scheduling helper. That dependency module and blank environment
fields are included; no new PSE endpoint is wired and no PSE catalog is changed.
The data-preserving startup guard is retained, including its legacy PSE-row
precheck. No migration is executed during handoff verification.

The inherited provenance-repair maintenance utility is the deliberately
redacted parser source: its personal contact and machine cache path are replaced
with `SEC_USER_AGENT` and `FINSIGHT_PROVENANCE_CACHE`. Missing monitored contact
fails before a request. Four legacy batch modules also have redundant EOF blank
lines removed to pass the outgoing whitespace check. Receipt pins describe these
review copies. These transport-only edits do not alter valuation rules or admitted seals.

## What is deliberately NOT in Git

`us700-private-runtime.tar.gz` is a separately prepared **server-only** package.
Its exact size, digest and membership count are in the receipt. It contains the
current immutable catalog/proof ancestry,574 recipes, runtime registry/policies,
and private compiled configurations for MAIN and parser. It contains no active
pointer, credentials, monitored SEC contact configuration, raw SEC caches,
database export or storage objects. It has not been transmitted by this branch
push. Arrange an approved private transfer before using it.

The tracked `backend/app/data/us_valuation_catalogs/active.json` intentionally
still selects the old100-entry catalog. **A clone alone will not serve700 or run
their calculators.** Missing server-only configuration fails closed. Do not
mistake the public list for the private runtime package or weaken hash checks.

This handoff does not make every historical batch test reproducible: many tests
still need the separately maintained SEC/PSE corpora and frozen review packets.
The current local650/600 rollback evidence remains retained locally; those
separate rollback roots and all historical source corpora are not transferred in
this current700 package. Private proof ancestry is not a complete audit corpus.

## Clean-checkout verification after private transfer

Use a fresh checkout of this branch. Install the backend requirements into a
dedicated environment. The historical parser requirements do not fully specify
its runtime: structural extraction also needs `arelle-release` and `lxml` as
used by the existing verified worker. Offline retention does not prove those
extraction dependencies or live SEC capture. Supply your own monitored contact
only when a separately authorized future source run requires it.

```sh
python3 scripts/stage_us700_handoff.py \
  --archive /private/approved-transfer/us700-private-runtime.tar.gz \
  --destination /private/new-us700-staging

python3 scripts/verify_us700_handoff.py \
  --private-root /private/new-us700-staging \
  --output /private/us700-http-proof.json

python3 scripts/verify_us700_offline_handoff.py \
  --private-root /private/new-us700-staging \
  --output /private/us700-offline-proof.json
```

Staging refuses an existing destination, changed archive, unsafe members or
conflicting configuration. It installs hash-pinned private configuration only
into the fresh checkout's ignored config paths. It never writes an active
pointer. Verifiers use disposable sandbox pointers, not your running system.

HTTP verification uses the real US router and ordinary production catalog
guards, with an ephemeral localhost token and no database/storage startup. It
checks all700 summary values/availability, selected details, numeric calculator
replay, unavailable calculators and protected POST authentication. Public GETs
are public by the existing router contract. This is not proof of full-app
authentication, database rate limits, browser UI, saved valuations or deployment.

Offline verification explicitly uses isolated-test permission and synthetic
metadata based on frozen identities. It launches the real worker/parser child
without a database job or SEC traffic. It proves retention/routing, not filing
freshness or successful new-source intrinsic recalculation.

After separate partner admission/activation approval, wire the catalog and
runtime mounts explicitly. The worker uses `US_REFRESH_CODE_ROOT=<checkout>` and
`US_REFRESH_CODE_WT=<checkout>/us_refresh_parser`, plus private catalogs/runtime,
monitored contact config and writable job-data directories. Recheck access,
cooldowns, schema, registry identities and all holds in that environment first.
This branch supplies no automatic activation or cloud deployment command.

## Verification record

See `US700-VERIFICATION.md` for observed checks, failures corrected in the
handoff-only harness, skipped tests and limitations. No new valuation was
calculated from filings for this handoff.
