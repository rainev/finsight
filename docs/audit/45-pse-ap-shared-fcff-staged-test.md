# Audit 45 — AP shared-starting-FCFF staged retest

**Status:** Isolated AP retest results user-confirmed on 2026-09-26 after verification of artifact arithmetic, deterministic output, catalog integrity, and all three calculator cases. **AP remains unapproved, not active, and not deployed.** RLC remains pending a consolidation-level property bridge. This was the user's requested simplification after the [prior AP test](44-pse-ap-staged-test.md) exposed a bear/bull calculator mismatch.

## Exactly what changed

The first test used different starting cash flows for bear/base/bull: PHP34,790.369m / **35,565.066875m** / 36,339.76475m. This retest uses the **same PHP35,565.066875m starting FCFF in all three**. The previously confirmed **25% interest-tax assumption, PHP138,809.675m JV book proxy, PHP21,872.575m minority cash-distribution proxy**, cash, debt, shares, five-year horizon, and each case's growth/ROIC/WACC/terminal assumptions were left unchanged. Thus bear/base/bull still represent different operating and financing cases—not fixed markups of a completed valuation.

| AP calculation-only PHP/share | Bear | Base | Bull |
|---|---:|---:|---:|
| Prior isolated test, different starting FCFF | 25.286 | **41.361** | 65.582 |
| **Shared-FCFF retest** | **26.312** | **41.361** | **63.741** |

The new intrinsic calculation has enterprise values of **PHP339,529.674m / 447,969.512m / 609,236.951m** and common-equity values of **PHP189,599.874m / 298,039.712m / 459,307.151m** (bear/base/bull). The derived low/high are PHP26.312–63.741/share. The calculation-only base remains **41.9% above** the locally active AP base PHP29.155/share; the >20% economic attribution and analyst sign-off from [Audits 43–44](43-pse-ap-proxy-recommendations.md) are still required. This is **not** a price target, investment recommendation, or newly approved issuer value.

## Isolated artifact and verification

The output is the one-issuer, non-serving [staged manifest](evidence/pse-ap-shared-fcff-staged-test-2026-09-26/PSE-V2-AP-SUPERVISED-2026-09-26-1.1/manifest.json) and [AP artifact](evidence/pse-ap-shared-fcff-staged-test-2026-09-26/PSE-V2-AP-SUPERVISED-2026-09-26-1.1/artifacts/AP.json), outside the app's active catalog root. Its exact issuer set is `{AP}`; status is `staged`, availability `intrinsic_valuation`, publication state `provisional`, with **zero approved entries** and no dated price/upside. The [builder](../../scripts/stage_pse_ap_supervised_test.py) gained an opt-in `--shared-starting-fcff` mode; its default mode reproduced the prior AP test's pointer, manifest, and artifact **byte-for-byte** (`34ef7f60…`, `1988b45d…`, `b002be6d…` respectively), preserving that historical result.

| Check | Observed result |
|---|---|
| Original source pins | The AP FY2025 and [1H2026 filing](https://pdswordpressbucket.s3.ap-southeast-1.amazonaws.com/wp-content/uploads/2026/08/Disclosure-No.-2960-2026-Quarterly-Report-SEC-Form-17-Q.pdf) SHA-256 hashes still matched the confirmed receipts before the isolated build. No original PDF was copied into the catalog. |
| Deterministic twins and integrity | Two independent retest builds and the staged output had identical pointer SHA-256 `25afa66195d078b9408399d1b01a2c580be74929a4a9a888670358f528f92dec`, manifest SHA-256 `a80fcdd3166b800b91ccf4e039609688ef16313d0e6d469e0a68b02698d6b021`, and artifact-file SHA-256 `e9c3326bc8256f30f2611e43fb1d9b077c54511563375e212ddea7b030cad930`. The input hash is `80b2dce5338ab4a90ea60918a303263c2f7d3448d6f78f4bba9c0820b746278a`; the internal artifact hash `e966a7cc0a5206bf890824d9da9275706f57de7d5f8beea0e616ee7886c5db17` verified. |
| Independent calculation | Decimal replay of all three FCFF cases matched artifact PHP/share within `1e-8`; base = PHP41.36077402036424. |
| Focused regression | **32 passed**, one existing `passlib`/`crypt` deprecation warning, across PSE model, contract, active API and calculator tests. No live product calculator or frontend code changed. |
| Authenticated isolated HTTP | No token: **401**. Test-token `GET /api/pse-valuations`: **1/1 AP, staged**; AP detail and calculator view: **200**; RLC detail: **404**. With **no overrides**, calculator POST for low/base/high exactly matched the staged values **PHP26.31192168996843 / 41.36077402036423 / 63.74083234255536**, with **0.0 baseline change** in all three cases. This exercised the real FastAPI router in an isolated in-process test, not a live browser. |
| Active readback | A separate authenticated read of the default route still returned **282/282 active**, AP base **PHP29.154683615845205**, RLC base **PHP61.81569315623288**. The active pointer SHA-256 stayed `50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92`; Batch 28 manifest SHA-256 stayed `8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7`. |

## Decision boundary

**The calculator mismatch is resolved for this isolated AP retest.** That does not resolve the economic questions: the starting FCFF remains a mechanical FY2025/TTM average, JV carrying value and the minority cash-distribution claim remain low-reliability proxies, borrowing-entity tax deductibility and other claims need analyst review, and the macro/WACC snapshot is dated. Durable source-storage/public-display rights have not been cleared. No full 282-entry refreshed candidate, production API/UI run, frontend build, approval, activation, scheduler, or RLC reconciliation is claimed. Stop here for user review; a later approval or publication action would require a separate explicit decision and its own end-to-end checks.

**Confirmation gate:** The user confirmed the shared-FCFF **staged test results** on 2026-09-26 and explicitly kept AP unapproved and RLC pending. Read-only checks at confirmation found the isolated pointer, manifest, and AP artifact byte hashes unchanged at the values above; the active Batch 28 pointer and manifest also remained unchanged. This confirmation accepts calculator parity and the observed calculation only. It does not approve AP's PHP41.361/share base, activate the isolated catalog, resolve the economic/source-rights gaps, or advance RLC or Phase C automation.
