# Batch 47 Merchant-Energy Recovery Result

Date: 2026-09-08
Status: user-confirmed; recovery and bookkeeping complete.

## Outcome

The one authorized recovery attempt covered exactly **NRG, VST and CEG**.

- Recovered to Conditional: **0/3**
- Still Withheld: **3/3**
- Final Batch 47: **0 Pass / 7 Conditional / 3 Withheld**, numeric **7/10**

Each issuer has a mechanically finite private residual-income diagnostic, but none has comparable normalized merchant
earnings suitable for publication:

| Ticker | Private diagnostic bear/base/bull | Recovery outcome | Why it remains private |
| --- | ---: | --- | --- |
| NRG | $29.95 / $34.04 / $39.58 | Withheld | LS Power/CPower and hedge/capital-return effects break the comparable parent history |
| VST | $21.30 / $23.67 / $26.85 | Withheld | Extreme preferred-adjusted ROE and payment-dated hedge/project obligations remain unresolved |
| CEG | $109.82 / $126.51 / $149.26 | Withheld | June equity is post-Calpine while annual history is pre-combination and merchant/nuclear adjustments remain mixed |

These diagnostics are not public values. Public low/base/high remain null, calculators remain unavailable, and no
missing hedge, project, claim or transaction value is replaced with zero.

## NRG

- Current common equity: **$4.205B** after $650M preferred; TTM common earnings: **$782M**; shares: **210.210M**.
- LS Power/CPower assets enter the current period without comparable post-acquisition annual GAAP history.
- GAAP derivative marks and unmatched customer contracts do not provide settled economic-hedge cash.
- Through July 31, reported repurchases/dividends were **$932M / $202M**, after the June balance date.
- PJM cleared **6,839 MW at $325/MW-day for 2028–2029**; that is future revenue context, not current value.

## VST

- Parent stockholders' equity **$5.482B**, less $2.476B preferred, gives **$3.006B** common equity; NCI is $12M.
- FY2024/FY2025/current raw ROEs are about **79.7% / 28.7% / 72.0%**, which are not sustainable regulated returns.
- Q2 includes a reported **$472M unrealized hedge loss** expected to settle in future years.
- NDT, ARO, Moss Landing, nuclear fuel, project financing and pending Cogentrix/Meta/Helix economics lack one
  payment-dated parent cash schedule.

## CEG

- Parent equity rose from **$14.517B** at FY2025 to **$31.977B** in June after Calpine, a **120.3%** increase.
- TTM unrealized derivative gain: **$132M** (`-$645M + $589M - (-$188M)`).
- H1 acquisition cash, long-term debt issuance and short-term debt issuance: **$2.537B / $5.001B / $4.500B**.
- The approximately **$860M** Brazos Valley sale remains pending and is not added to current value.
- Pre-Calpine annual history cannot normalize post-Calpine hedge, tax-credit, decommissioning, PPA, integration,
  project-debt and NCI economics.

## Independent challenge

Three Luna High reviewers independently challenged NRG, VST and CEG. Sol replayed all diagnostics, checked event hashes,
verified preferred/NCI scope, and confirmed that no source-backed merchant normalization or cash schedule was missed.
No unresolved Critical, Important or Minor implementation finding remains; the three economic model gates remain.

## Determinism and verification

- Final candidates: `output/batch-47-recovery-run-b-20260908` and
  `output/batch-47-recovery-run-c-20260908`; reports and all private/public artifacts are byte-identical.
- Recovery tree SHA-256: `e350f7c17e71ab63a23dbb1cd8ec4f3d0d2133bfd773914a2033eddcffe8887e`.
- Recovery report SHA-256: `53471f331022bf15c05608ca6bf7e51f63ae2baad8a8de4632a8c56cab27cbab`.
- Focused Batch 47 initial/recovery/bookkeeping tests: **21 passed**.
- Complete backend regression: **1,917 passed / 3 skipped / 0 failed**.
- Frontend production build: **passed** (`1,694` modules transformed).
- Immutable recovery catalog: `US-RESET-2026-08-14-B01-B47-RECOVERY-1.0`; two builds are byte-identical.
  Manifest SHA-256: `d75a1ddb70f1a5879d040265f84402e8be22091bb63c3202dc60e780212c0481`;
  artifact-tree SHA-256: `738f4bea471413bce22fd183d6371024310ec3d95514d67d5b648f5aeb35ccfc`.
- Real isolated API: **470/470** list/detail exact catalog parity, **470/470** calculator-default parity, zero private
  leaks and zero forbidden serving imports. Evidence receipt SHA-256:
  `05472e26cd73f56e8a03dc0ee03e6bb635ed2b32a1855366166f78045a13e471`; calculator receipt SHA-256:
  `621e21ce7376d608638d857d9c7682eb954c691e947767c9fb8c6e003daf1a72`.

## Confirmation and bookkeeping boundary

If confirmed, the 470-company universe remains **116 Pass / 330 Conditional / 24 Withheld**, with **446/470 numeric**.
All ten Batch 47 issuers will enter the Recovery Learning Watchlist: seven Conditional and three withheld after recovery.
The watchlist will become **354 entries: 330 Conditional / 24 Withheld**. NRG, VST and CEG will be appended once to the
cumulative automatic-withheld history, increasing it from 31 to 34 entries.

The user confirmed the recovery result. The 470-company universe remains **116 Pass / 330 Conditional / 24 Withheld**,
with **446/470 numeric**. The Recovery Learning Watchlist now contains **354 companies: 330 Conditional / 24 Withheld**
and has SHA-256 `2ed1b095bc5e93d32b0830d2a9e780911c9de9116087b6ac07563994b3182b5f`. NRG, VST and CEG were appended once to the
cumulative automatic-withheld history, which now contains 34 entries and has SHA-256
`cbfa072dc2a255f5ed95ea903f740a31e58c78ecf0cad5c8a61cff30a462dadd`.

Batch 48, serving promotion, merge, push and deployment remain outside this authorization.
