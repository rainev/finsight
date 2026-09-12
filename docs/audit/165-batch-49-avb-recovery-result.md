# Batch 49 AVB Recovery Result

Date: 2026-09-12
Status: user-confirmed; bookkeeping verified.

## Outcome

The single authorized recovery attempt covered exactly **AVB**.

- Recovered to Conditional: **0/1**
- Still Withheld: **1/1 — AVB**
- Final Batch 49 candidate: **0 Pass / 9 Conditional / 1 Withheld**, numeric **9/10**

## Why AVB remains Withheld

Both practical routes were exhausted with cutoff-safe evidence:

- Standalone AVB reported H1 Core FFO of $5.69 per share. H1 asset-preservation capital was $106.450M and
  NOI-enhancing capital $63.714M, but those schedules exclude development and certain newly acquired-community costs.
  Full-year EPS/FFO/Core FFO guidance was suspended because of the merger.
- A private standalone diagnostic uses annualized Core FFO less reported preservation capital and produces
  **$129.95 / $138.91 / $149.20**. It is not public because the AFFO reconciliation is incomplete and the standalone
  economic object was expected to expire at closing.
- Shareholders approved the EQR merger on August 12 with a fixed 2.793 exchange ratio and expected August 17 closing.
  The available combined statements are preliminary GAAP pro formas, not combined AFFO, and lack final shares,
  debt/cash, purchase accounting, integration costs and capital policy.

No post-cutoff Vivmark facts, transaction-price shortcut, unsupported synergy, zero substitution or stale standalone
value is published. AVB retains a null range and unavailable calculator.

## Independent challenge and verification

Three Luna High reviewers separately challenged the standalone evidence, combined-company route and public safety.
Sol replayed the private diagnostic, verified event/source hashes and confirmed the hard blockers:
`MAJOR_EVENT_UNBOUNDED`, `AFFO_RECONCILIATION_UNAVAILABLE`, `POST_COMBINATION_HISTORY_INCOMPLETE`, and
`MODEL_UNSUPPORTED`.

- Final candidates: `output/batch-49-recovery-run-c-20260912` and
  `output/batch-49-recovery-run-d-20260912`; all private/public/report files are byte-identical.
- Recovery report SHA-256: `950d776e8ed8ec6ddad32fc8dcd328e51b3568fd33fc991ec9dfcc5b614c425f`.
- Recovery candidate-tree SHA-256: `b5b6b772294de25358d09cc93777f45f86a1f53b21cfd497fbf682cc8d54d4e9`.
- Focused Batch 49 history/recovery/calculator tests: **18 passed**.
- Complete backend suite: **2,362 passed / 3 skipped**.
- Frontend TypeScript and production Vite build: **passed** (`1,694` modules transformed).
- Deterministic cumulative catalogs: `output/batch-49-recovery-api-runtime-c` and
  `output/batch-49-recovery-api-runtime-d`; both contain exactly **490** artifacts and share manifest SHA-256
  `e8930b09054ba7cfba35913e3347c98a79ff14a5a2e006df8d5ca72acf40fbe7` and artifact-tree SHA-256
  `ae28b2712fe1d3d3dca6748c920fc3d6247b2c10833a12b4004f07313024bbec`.
- Real isolated API: **490/490** list/detail exact catalog parity, **490/490** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Launch-first receipt SHA-256:
  `8f43f8b3891df1daa6ee776959e50e3ffc6408f021082323e96e1ddfd42d20c6`; official-evidence receipt SHA-256:
  `2f2387cb3adf4ee7e3a90930657824e8a824b4c040e8635865dbaec5bc4a38b8`.

## Boundary

The user confirmed the result. All ten Batch 49 companies were appended to the Recovery Learning Watchlist and AVB was
appended to the cumulative withheld register:

- Recovery Learning Watchlist: **374** total — **348 Conditional / 26 Withheld**; SHA-256
  `5c44900a42262a55debe3192b239731c6c38ecf8d4fc2253e477ac07f4ea3f22`.
- Cumulative automatic-withheld register: **36** entries; SHA-256
  `f1507416aefdc01113104902c13c62ebc97954832c048fe03bb80b195e565ee4`.
- Bookkeeping contract tests: **10 passed**.

Serving artifacts remain unchanged. Batch 50, merge, push and deployment require separate authorization.
