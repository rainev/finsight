# Controlled reset evidence ledger

## CR0 — protected baseline

- Branch/commit: `codex/period-aware-valuation-policy` at `27c2cdad8b126e3b0aa2bb2421499bc3607eec07`.
- Baseline suite: `996 passed, 3 skipped`.
- Serving hash: `34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.
- Serving outcomes: 206 total; 88 finite review-required; 118 withheld.
- Batch 01 comparison: 5/10 finite and 5/10 withheld.

## CR1 — immutable manifest and private governance

Intent: every fixed issuer loads one immutable private economic profile and model decision;
no route can publish before source and model validation.

- Manifest contract: 2 focused tests passed.
- Governance contract: 4 focused tests passed.
- Real loader exercise: 10/10 records loaded in manifest order; all carried one accession and
  remained `routing_status=hypothesis`, `reliability_cap=Withhold`.
- Serving hash after CR1: unchanged.
- Independent challenge: Sol High substitute (Luna unavailable) identified DELL captive-finance,
  NEE mixed-utility, O AFFO/NAV, WDC cyclical-normalization, software-intangible, bank common-
  equity, and specialist-fact-lineage gaps. Those gaps informed the private hypotheses; no
  model was promoted to selected.

## CR2 — source packet tooling and live blocker

Intent: capture exactly ten immutable point-in-time SEC packets without serving writes.

- Packet/help/schema/immutability tests: 4 tests passed.
- Structural filing round-trip and malformed-payload tests: 5 added checks passed within the
  focused structural suite.
- Complete backend suite after correcting the unsupported-form boundary:
  `1011 passed, 3 skipped`, one Passlib/Python `crypt` deprecation warning.
- Direct CLI help succeeded without `PYTHONPATH` and without importing Arelle.
- Live command attempted:
  `python3 scripts/capture_batch_01_sources.py --output-root output/batch-01-controlled/sources`
- Live result: exit 1 before the first request — `A monitored SEC User-Agent is required for a
  network fetch (example: 'FinSight contact@example.com')`.
- Packet directories created: 0/10.
- Serving hash after the failed acquisition: unchanged at
  `34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.

The user then supplied a monitored SEC contact. Network acquisition completed with:

`{"manifest_count": 10, "serving_artifacts_changed": false, "source_packet_count": 10}`

- 10/10 manifest identities and CIKs match.
- Every emitted payload hash matches its packet manifest.
- Every eligible-ledger filing has `filed <= 2026-08-14`; future filings are separate.
- A cached rerun returned the same 10/10 result without network refresh or byte changes.
- Latest eligible filing candidates range from CRM's 2026-05-28 10-Q through WDC's
  2026-08-14 10-K; their accessions and packet hashes are preserved in the untracked evidence.
- Companyfacts diagnostic replay: 5 old-route numeric candidates (MSFT, JPM, BAC, NEE, O) and
  5 withheld FCFF cases (AAPL, CRM, ANET, WDC, DELL). These are diagnostics only; all ten remain
  private routing hypotheses and none is approved for publication.
- Serving hash remains unchanged.

Offline structural verification then completed for the five FCFF cases with supported gaps:

- Attempted/parsed/failure: 5/5/0.
- Requested decisions: 19.
- Accepted/review/rejected/unresolved: 1/0/10/8.
- The sole accepted decision is CRM `finance_lease_total = $664,000,000` from accession
  `0001108524-26-000127`; it remains shadow-only pending governed production promotion.
- AAPL, ANET, WDC, and DELL retained explicit rejected or unresolved current-filing gaps.
- Runs `structural-shadow-run-a` and `structural-shadow-run-b` each contain 22 files and have
  the identical tree hash `1575f0ab2116ea599a6a2362332f93591af86d0cd97963e36a6921387cd649f6`.
- Serving hash remained unchanged and Arelle remained outside the FastAPI import path.

CR2 is firsthand verified. CR3 starts with all ten routes still capped at `Withhold`; the
structural parse does not override missing model maturity or promote shadow evidence.

## CR3/CR4 — controlled outcomes and real consumer verification

- Controlled outcomes: 10 attempted, 0 numeric, 10 withheld, 0 invalid input.
- Processing completion: 10/500; publishable numeric completion: 0/500.
- Structural evidence promoted to the private valuation path: CRM finance-lease total only.
  The exact proof clears the old bridge blocker but not CRM's experimental-model/input blockers.
- Shared model adapters have hand-calculation tests and no issuer defaults.
- Valuation runs A/B are byte-identical with tree hash
  `5c111bba5f880cc909b1deae36365dc3167377916e4ebe176af28f6e75d6e681`.
- Full backend suite: 1040 passed, 3 skipped, one existing deprecation warning.
- Earlier-company replay: 106 candidates, 104 valid private, 94 source-verified, 1 Low numeric,
  6 build errors, 4 source failures, 2 invalid inputs, 0 unsafe promotions; two reports identical.
- Real staged FastAPI: list 200 with 10 items; 10/10 details 200; all null/withheld/Low public
  safety label; no private fields; zero Arelle modules on serving import; clean shutdown.
- UI check deferred because the frontend runtime is absent and the route requires authentication.
- Serving hash remains `34b380fe6678af826fbd63cb53b3fd737a596631e86bbb93346ad04e10c1e00a`.

Batch 01 is **verified — user confirmation needed**. No artifacts qualify for promotion.

## PB0–PB4 — practical bounded-uncertainty policy

- Strict comparison: 10 attempted, 0 numeric, 10 withheld.
- Practical outcome: 10 attempted, 7 numeric Low, 3 withheld, 0 invalid.
- Newly numeric: AAPL, MSFT, CRM, ANET, JPM, BAC, O.
- Still withheld: WDC (cycle range unbounded), DELL (DFS allocation unbounded), NEE (latest
  quarter extraction absent; mixed-business value unbounded).
- Practical runs A/B are byte-identical with tree hash
  `8a3e601e42162b6cf00fd23f106f344f3acac5fe3cf3c7a4cf5ef87a4f835684`.
- Focused verification: 220 passed, 3 skipped. Complete backend: 1068 passed, 3 skipped.
- Earlier-company regression replay: 106 candidates, 0 unsafe promotions, 0 public-contract
  failures, no serving changes, deterministic report hash
  `db42ad8e0fe91487c44971ff0672145ef42b7b45cdd6ddcca036407c9b350f4c`.
- Terra Medium evidence audit: PASS. Sol High substitute economic re-challenge: PASS. No
  Important or Critical finding remains.
- Real staged FastAPI: list 200 with exactly 10; 10/10 detail 200 and list/detail parity; no
  private fields; zero Arelle serving imports; clean shutdown.
- Serving roots remained byte-identical before/after. No promotion was attempted.

Practical Batch 01 is **verified — user confirmation needed**. Full comparison and exact values:
`docs/audit/12-practical-batch-01-result.md`.

## RR0–RR5 — WDC, DELL, and NEE recovery

- Recovery target/outcome: 3 attempted; WDC and DELL numeric Low; NEE withheld on nonpositive
  bear/base FCFE. Final Batch 01: 9 numeric Low / 1 withheld / 0 invalid.
- Exact recovery source trees B/C are identical:
  `00e5eb9bffa294b6314ae7d005bcbde029a908c90b9ffe61bbe1e71749926b8e`.
- Final valuation trees A/B are identical:
  `6af0af0f0c5adc29697c71cbb713e9b1676d80c2a1e5c6b16e34c4b2a892ef73`.
- Sol High substitute final challenge: PASS, no Important/Critical issue remains.
- Focused: 108 passed, 3 skipped. Complete backend: 1078 passed, 3 skipped.
- Earlier-company replay: 106 candidates, zero unsafe promotions, zero public-contract failures,
  deterministic report hash `db42ad8e0fe91487c44971ff0672145ef42b7b45cdd6ddcca036407c9b350f4c`.
- Real staged API: exactly 10 list items, 10/10 detail HTTP 200, list/detail parity, no private
  fields, zero Arelle serving imports, clean shutdown.
- Serving roots remained byte-identical; nothing was promoted.

Recovery is **verified — user confirmation needed**. Full evidence:
`docs/audit/13-three-company-recovery-result.md`.

## U0 — replacement universe and frozen Batch 02

- NEE is recorded as the first cumulative post-recovery withheld entry.
- The original historical 500 proof failed safely: serving=206 unique CIKs, legacy recovery=120,
  difficult replay=106, and no 500-row artifact in local files or reachable Git history. No
  company was selected from those outcome-selected subsets.
- The user then explicitly authorized an S&P 500 issuer universe effective 2026-08-14.
- Pinned public membership, official S&P AVB/RDDT cutoff evidence, and a captured SEC ticker map
  reconcile 503 securities to exactly 500 issuer CIKs, including three explicit multi-class
  choices and one historical EQR CIK exception.
- Two source captures produce the same canonical manifest SHA-256
  `cc11df21ee64c5e6ff6cc49fb20f7dbb7b05f1f23b7eea6acea4b190720e8a8b` despite mutable raw
  notice bytes; normalized change evidence is identical.
- Locked Batch 01 plus 49 future batches exactly cover 500 CIKs. Every future batch is 8 core +
  2 economically predeclared boundaries and has at most two partition cohorts. Two fresh freezes
  match with root `fd49977122da8bdbaad1d336efeb5bf8480a21a3c63d03b57c0b961cb65908a4`.
- The initially mechanical boundary partition was rejected and replaced; the final version has
  truthful issuer lanes and 13 named cross-sector exceptions.
- Batch 02 is OMC, VZ, T, TTWO, NFLX, CHTR, CMCSA, TMUS, META, and WBD. It is frozen but no SEC
  packet or valuation has been created.
- Fresh cached-source reconstruction exactly matched the frozen 500-issuer manifest. Fresh
  partition output/config mirrors exactly matched all stored batch files. Complete backend suite:
  `1089 passed, 3 skipped`; serving hash remained
  `8b8f3e1bd6783b43d658253c6b04d71c13ea693df63a4bebe402aac514f87cac`.
- GoodBehavior adoption was already present. The configured source update advanced
  `83460a2a` -> `601e9740`; one hook updated, nine files unchanged, zero conflicts, and a second
  dry run reported already up to date.

Universe/partition freeze is **verified — user confirmation needed**. Await `Process frozen Batch
02.` Evidence: `docs/audit/16-universe-freeze-and-batch-02-manifest.md`.

## B02 — controlled initial processing

- Exact denominator: 10/10 attempted; no substitutions.
- Source packets: 10/10; structural Arelle packages: 10/10 parsed, zero failures; 51 future
  filings excluded from the eligible ledger.
- Strict result: 0 numeric / 10 withheld. Practical result: 4 numeric Low (VZ, T, NFLX, TMUS) /
  6 withheld (OMC, TTWO, CHTR, CMCSA, META, WBD) / 0 invalid.
- Independent Luna-High final challenge: PASS, no Critical/Important finding after current debt,
  tower obligations, spectrum cash, annual lineage, AT&T scope, Netflix commitments, and META
  commitment treatment were corrected.
- Verified runs A/B are byte-identical with hash
  `fdb0a830fb724c07c59fe8cdc04016df55427e9303ebe83372da5182d7d1a25d`.
- Focused: 41 passed. Complete backend: 1103 passed, 3 skipped. Prior 94 public artifacts:
  zero sanitizer exceptions/changes. Serving roots unchanged.
- After explicit user approval, real Uvicorn served only the staged Batch 02 directory: list HTTP
  200/count 10, details 10/10 HTTP 200, exact list/detail/file parity, zero private-field leaks,
  zero Arelle serving imports, and clean shutdown.
- No recovery, cumulative-register change, Batch 03 work, serving promotion, merge, or deploy.

Batch 02 initial processing is **verified; recovery subsequently completed below**. Evidence:
`docs/audit/17-controlled-batch-02-initial-result.md`.

## B02-R — one-attempt recovery and final register

- Recovery denominator: OMC, TTWO, CHTR, CMCSA, META, WBD; exactly six attempted once.
- Public-method research adopted only transparent model-selection/history/flow-consistency/
  predictability practices from Alpha Spread and GuruFocus; zero proprietary formulas or displayed
  competitor values were used.
- Recovered numeric: 0/6. Still withheld: 6/6. Final Batch 02 remains 4 numeric Low / 6 withheld.
- WBD `$31.00` plus ticking consideration is retained only as a private conditional transaction
  diagnostic, never intrinsic value and never probability-weighted.
- An Important receipt-period bug was fixed: exact submissions `reportDate` now controls all six;
  final independent Luna-High verdict PASS.
- Verified A/B hash:
  `6a46fe37c0421307ee1f2c22d1d5b5a56c5ae4a616ad5c8f25234c1a569ee7b6`.
- Focused: 40 passed. Full backend: 1107 passed, 3 skipped. Real API list 200/count 10,
  details 10/10 200, exact parity, zero private leaks, clean shutdown.
- Cumulative withheld register now contains seven entries: NEE plus all six Batch 02 holdouts.
- Serving roots unchanged; no promotion, Batch 03, merge, or deploy.

Batch 02 recovery is **verified — user confirmation needed**. Evidence:
`docs/audit/18-batch-02-recovery-result.md`.
