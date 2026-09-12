# WG12 preferred and temporary-equity claims

Verified 2026-09-10; user confirmation pending. This is a bounded working-group
result, not release approval. Production, scheduling, merge, push, deployment,
later batches and family adapters were untouched.

## Retained mechanism

COHR and WMB share a current preferred/temporary-equity lifecycle contract:
select current issuer balance-sheet claims, keep NCI separate, retain par/share
facts as diagnostics, and require settlement roll-forwards before treating an
old claim as zero. The rules contain no filing dates or amounts.

COHR is the representative settled-conversion case. Current temporary-equity
carrying amount, redemption value, issued shares and outstanding shares are all
zero. The same filing reports 215,000 preferred shares converted, a
-$2.506885B temporary-equity conversion value, and a 12.419M common-share EPS
conversion effect. Historical preferred terms are not carried forward. Current
NCI is $334.705M. The existing $1.2941594442234704B bear cash-gap stress is
preserved as a signed nonoperating adjustment, not preferred equity.

WMB is the difficult current-carrying case. The filing reports $35M preferred
stock, 35,000 issued Series B shares, $1 par value and a matching $35M preferred
equity roll-forward component. The $35M—not par—is the current claim. Separately,
NCI is $2.178B. Those components exactly reproduce the prior $2.213B total claim,
but WMB remains review-only because issuer cash cannot yet be separated from the
$203M cash/restricted-cash aggregate and the current debt/investment coverage is
not fully bound.

## Five-company result

| Company | Classification | Previous low / base / high | Current low / base / high |
|---|---|---|---|
| COHR | Retained; settled convertible preferred, zero current claim, $334.705M NCI | 0 / 16.788931960143348 / 41.7124972189867 | 0 / 16.399946494134667 / 40.54510085312604 |
| WMB | Retained difficult case; $35M preferred plus $2.178B NCI | 0 / 15.439688427767331 / 41.84304198875888 | No candidate; prior dated estimate retained |
| HPE | Live Series C mandatory convertible; different conversion/dividend mechanism | 4.330120208040657 / 12.393012022735743 / 37.825097927260146 | No candidate; implementation gap preserved |
| LITE | Live one-for-one convertible preferred with no redemption claim; different event/dilution mechanism | 11.874045435982683 / 26.704663131255703 / 77.08109673376075 | No candidate; source/economic review preserved |
| PODD | Negative control: authorized but zero issued/outstanding preferred; par-only disclosure | 20.9540316590138 / 68.16473698232774 / 133.3411455051541 | No candidate; unrelated bridge review preserved |

COHR changes are 0 / -0.38898546600868045 / -1.167396365860661 per
share, or 0% / -2.3169160905060937% / -2.7986729246439968%. Current
source shares are locked at 201,531,246 instead of the legacy scenario-specific
195,832,246 / 195,609,623 / 195,387,000 range. Debt is corrected from the
legacy gross $3.257482B amount to $3.236457B of current debt, noncurrent debt and
finance-lease liability. The larger current dilution more than offsets the
$21.025M lower debt. Cash, current NCI and the bear cash stress remain intact.

HPE is not treated as absent merely because its preferred book line is zero. Its
current 30M preferred shares, $1.5B liquidation preference, 7.625% dividend,
September 2027 mandatory conversion and 76.056M–93.168M conversion shares need a
separate deterministic terms/event rule. LITE's 2.9M NVIDIA preferred shares are
one-for-one, pro-rata on liquidation and nonredeemable; the $1.9997B proceeds are
APIC financing, not a claim. PODD reports zero preferred shares and value; its
convertible notes remain debt evidence, not preferred stock.

## Verification evidence

- COHR controlling filing: accession `0000820318-26-000020`, period
  `2026-06-30`; structural SHA-256
  `cda693f7a11395fdf021bf81c12641f7b55f496a51e658405b51eb1268b8cc6d`;
  raw filing SHA-256
  `1a6f1dca0644b3ef0092fb15e26d420af36c136a22a70866a56927a441d53a0e`.
- WMB controlling filing: accession `0000107263-26-000026`, period
  `2026-06-30`; structural SHA-256
  `52b6e5f14e4cecfaf7b8363b19035af0edf7db197cc46b845e291cbbe419dbc2`;
  raw filing SHA-256
  `991a36329ca5d7cc9a2658380cc9653fe094a8cf7eb712f3218feaeb83606cda`.
- Five-company direct source report:
  `output/us-refresh-runtime/source-validation/069c0e86ec27605119b8627e661ab36ebfc74cdcf892f1a732e76dd696f89a9b/report.json`,
  SHA-256 `069c0e86ec27605119b8627e661ab36ebfc74cdcf892f1a732e76dd696f89a9b`.
- Frozen two-worker retained group:
  `output/us-refresh-group-verification/19e2a34d965e2bdffdb596aea40143664278897078d13b9bb65fd95e2750228b/report.json`,
  SHA-256 `11eff57b8443ea6b85cda163f00596f6583a1a0c7047bf380cd12ca42f4753e7`.
  Outcome: one source-bound candidate and one exact source/economic review.
- Focused regression: 143 passed; one unrelated dependency deprecation warning.
- Isolated COHR API/database UAT:
  `output/us-refresh-operational-uat-20260909T164013Z-1ff60e1f/uat-report.json`,
  SHA-256 `dac57b4ebb850cd3f85cc80ed2d13c6b994af0a26f0a0aba3f1795f0002a7271`.
  A real FastAPI worker served predecessor/candidate/rollback values, reloaded
  without restart, rejected stale CAS and preserved 440 companies plus 419
  private recipes. Production was not touched.
- Work register: `output/us-refresh-work-register.json`, SHA-256
  `f978e32cdced2bf57d8b3da057450750da8b5a6b9ba2e9df46c5ad79faa87e5a`.
  Counts: 261 compiled contracts, 158 implementation gaps, one current-policy
  source-bound result and zero explicit successive-period proofs.

Two Luna xhigh reviewers independently inspected COHR/HPE and LITE/PODD. The
primary agent separately inspected WMB, integrated the shared rule, reran the
source calculations, and verified the current runtime evidence.

## Remaining blockers

- WMB needs a source rule for its inseparable cash/restricted-cash aggregate,
  current/noncurrent debt and finance-lease coverage, and entity-scoped
  securities before a new value can be issued.
- HPE needs a deterministic mandatory-conversion/dividend schedule spanning its
  current 10-Q, governing 10-K terms and current 8-K dividend evidence.
- LITE needs its cutoff-safe earnings-release bridge and one-for-one preferred
  dilution integrated without double counting; generic lease/NCI/investment
  fields remain unresolved.
- PODD's preferred classification is complete, but its cash/debt/marketable/NCI
  bridge remains unresolved and was not hidden by the negative-control result.
- No company has successive-period proof under the current release candidate.
