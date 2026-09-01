---
name: structural-wrapper-output-is-a-reusable-cache
description: Offline structural replay must recognize a completed batch wrapper as a cache, not only the older official-evidence packages/parsed layout.
metadata: { type: gotcha }
---
A completed batch structural root already contains the immutable controlling
`package-manifest.json` and `structural-filing.json` under each ticker. A replay helper that only
recognizes the older `packages/<ticker>/...` plus `parsed/<ticker>/...` official-evidence layout
will falsely report a cache miss and fall through to a network fetch.

**Why:** Batch 12 source replay was fully local, but structural replay initially tried SEC because
the reuse helper could not consume its own prior wrapper output. That violates the cache-first
expectation even though all needed evidence is already present.

**How to detect / apply:** run a replay with the completed wrapper as `--reuse-root` and require
all tickers in `reused_tickers`, no captured tickers, and byte-identical A/B output. Validate CIK
and controlling accession before accepting either cache layout.

Batch 14 exposed the partial-run version of this trap. An interrupted structural run completed the
TECH wrapper and HCA filing package before stopping. Retrying into the same immutable output root
failed because the valid TECH receipt changed from `capture_mode: captured` to `reused`, so its
bytes were intentionally different.

**How to detect / apply:** preserve the partial output and package cache. Resume into a new output
root, include the partial wrapper plus older package roots in `--reuse-root`, and require the final
summary to show all ten parsed with protected roots unchanged. Then replay the completed root twice
and compare bytes. Never delete or overwrite the partial evidence merely to make the retry pass.
