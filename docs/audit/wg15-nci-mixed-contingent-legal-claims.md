# WG15 NCI mixed with contingent and legal claims

Verified and user-confirmed 2026-09-12. This is a bounded working-group
result, not release approval. WG15 did not invoke production activation,
scheduling, merge, push, deployment, later batches or family adapters. During
the shared-worktree run, HEAD moved externally to pushed Batch 50 commit
`4fa0a64`; that commit contains the WG15 code and focused tests. This audit and
the roadmap status update remain uncommitted.

## Retained mechanism

ABT and BAX use versioned source rules that keep ordinary NCI, acquisition
contingent consideration, legal/environmental accruals, separation
indemnification and disposal-group claims in distinct economic slots. Matching
aggregate and Level-3 presentations are counted once. Duration payments,
possible-loss ranges, historical or aggregate maxima and owner flows remain
non-additive diagnostics.

ABT is the representative current source-bound case. The current filing binds
$652M ordinary NCI, $263M contingent consideration and a $510M scoped
legal/environmental carrying accrual. Its Exact Sciences pro-forma revenue is
selected from the acquisition member and annualized from the reported six-month
period; the rule does not contain a filing amount or date. Historical cash
conversion remains the margin basis, and the current reported share denominator
is locked across scenarios.

BAX is the difficult case. Its $10M contingent consideration, $43M separation
indemnification and $52M disposal-group claim form a $105M current claim stack.
The negative $27M ordinary NCI is retained in evidence but projected to zero for
valuation so it cannot become a common-shareholder asset. The $133M aggregate
maximum, $28M retained guarantees, $39M legal reserve, $25M environmental subset
and $31M paid contingent-consideration cash remain separate. Its full valuation
still fails closed on commercial-paper and marketable-security scope.

BA was inspected and retained only as a source-proved NCI subcase. Its $15M
ordinary NCI is separate from NCI earnings and owner flows, but the live
mandatory-convertible preferred instrument, $971M environmental accrual, $1.115B
possible-loss amount, guarantees and repurchase commitments require separate
rules. BA remains an implementation gap; no candidate was manufactured.

## Company results

| Company | Classification | Previous low / base / high | Current low / base / high |
|---|---|---|---|
| ABT | Source-bound representative; $652M NCI + $263M acquisition claim + $510M legal/environmental accrual | 29.689388909506913 / 58.20809920073297 / 89.65169838253692 | 30.395758666637082 / 58.139498474687564 / 87.30738903369902 |
| BAX | Difficult case; $105M claim stack and negative $27M NCI treatment compile, but cash/securities bridge remains unresolved | 0 / 8.54935871774756 / 27.122993321184648 | No candidate; source/economic review |
| BA | $15M ordinary NCI is source-separable; preferred conversion and legal/guarantee scopes remain outside this rule | 0 / 4.039475664565482 / 60.95483472313898 | No candidate; implementation gap |

ABT changes are +0.7063697571301688 / -0.06860072604540335 /
-2.3443093488378963 per share (+2.3791993809073597% /
-0.11785426252939324% / -2.6149079059661573%). The claim
reclassification is value-neutral. The movement comes from replacing the prior
scenario-sensitive 1.78863935B / 1.745014B / 1.70138865B shares with one current
reported 1.747073B denominator while preserving the filed $49B annualized
pro-forma operating scale, historical margins and full $1.425B claim burden.

BAX's targeted reclassification from a $105M legacy preferred slot to a signed
$105M nonoperating claim, with valuation NCI zero, reproduces its previous range
exactly: delta 0 / 0 / 0. It is not a current candidate because its separate
cash/securities source gaps remain open. BA has no justified replacement range.

## Source evidence

- ABT controlling 10-Q: accession `0001628280-26-050134`, period
  `2026-06-30`, filed `2026-07-28`; structural SHA-256
  `e568265e70be188b285e9cb8632a4e5db7da488f84eedc7a7b89c5d503660901`;
  source-packet manifest SHA-256
  `c4cc04be860a149427af98c672dea3d6fbdc6efe97d73808f0b33c7cc0c358dd`.
- BAX controlling 10-Q: accession `0001628280-26-051118`, period
  `2026-06-30`, filed `2026-07-30`; structural SHA-256
  `e4d19ea93c65b0f1108dfd1c20503e1fda1a7f95aac23191e30c66ece08c6ced`;
  source-packet manifest SHA-256
  `96b77e33272bf74590ccc7369689569eac1806feb5b0c08a21f7a1f0e9138c2b`.
- BA controlling 10-Q: accession `0001628280-26-050038`, period
  `2026-06-30`, filed `2026-07-28`; structural SHA-256
  `af0bce28600668233c58e426a0a12a74a5f0f979a080d9d0941520e8d656133c`;
  source-packet manifest SHA-256
  `b8b04112d57f768b99cc1692283450b15fe93c6e7c7cb46a700775e924dfc9eb`.
- Frozen source index:
  `output/us-refresh-runtime/source-indexes/3f708765d48cd7c5e24782deae53fc6b4714a3a51c9b7372e2c3e485bfc33ee4.json`,
  file SHA-256 `b696cb36ef36d4e9d7adb021c69d33f3ca94673310eb9c053611c800f4c46a5f`.

## Verification evidence

- Direct real cached-source report:
  `output/us-refresh-runtime/source-validation/740aa6772578dd88fbb2e061cb1c20a7c99682b67941c4b52ba70af127324c88/report.json`,
  SHA-256 `740aa6772578dd88fbb2e061cb1c20a7c99682b67941c4b52ba70af127324c88`.
  Outcome: ABT source-bound, BAX source/economic review, BA implementation gap.
- Frozen two-worker group:
  `output/us-refresh-group-verification/01edc57c62b6947e045abadb40ebc33a443bce75c11fdc491178ec82a6394d8b/report.json`,
  SHA-256 `3ddce1fdf281b6e52e4c3349f452e8bd6aa5f6aca9de657db56e484fe6eb120b`.
  It reproduced one source-bound candidate, one source/economic review and one
  implementation gap on implementation SHA-256
  `d4c631497f04dfb4cca7f58347077f138da0a09c02aed6789aa1179c7a442251`.
- Focused regression: 150 passed in 409.16 seconds. It covers mixed claims,
  acquisition, litigation, reported-NCI projection, bridge scopes, preferred
  lifecycle, financial normalization, operating compilation/bindings and the
  two-worker flow. Adversarial tests reject unexpected positive dimensions,
  duplicate conflicts and a BAX environmental subset exceeding its total.
- Isolated ABT API/database UAT:
  `output/us-refresh-operational-uat-20260912T072050Z-99dfb3a1/uat-report.json`,
  SHA-256 `6fe2d110976ef8ef2b4d58942e68d61a016b1857274ad7e418728b2827813cb4`.
  A real FastAPI worker served predecessor → candidate → rollback, reloaded the
  candidate without restart, rejected stale CAS, and retained 440 companies and
  419 private recipes. The first sandboxed attempt could not bind localhost;
  the approved isolated rerun passed. Production was not touched.
- Current policy SHA-256:
  `44dc078e2e0d667ea3d83c252d9c2140b3a5b79ee5c585222b3acb1e70ac907f`.
  Readiness remains correctly blocked at 419 recipes / 265 compiled contracts,
  exit 2, `activated:false`. `git diff --check` passed.
- Current work register: 440 companies, 419 recipes, 265 compiled contracts,
  154 implementation gaps, 1 current-version source-bound result and 0
  successive-period proofs.

Three Luna agents independently reviewed ABT, BAX and BA. The primary agent
rechecked their cited source rows, hardened dimension and duplicate rules,
rejected the first ABT candidate when it dropped the filed pro-forma scale, and
then verified the corrected calculation and real API path.

## Remaining blockers

- BAX requires complete current commercial-paper and current/noncurrent
  marketable-security scope. The claim rule is compiled, but claim correctness
  does not clear that independent bridge gap.
- BA requires a dedicated mandatory-convertible rule and separately reconciled
  environmental, possible-loss, guarantee and repurchase scopes. Its $15M NCI
  proof does not clear those claims.
- ABT is source-bound only for this frozen current filing; no successor filing
  has yet demonstrated a successive quarterly refresh.
- No company has successive-period proof under the current release candidate.
- Git history changed externally during the shared-worktree run: current HEAD
  and `origin/codex/universe-reset-batch-50` are both `4fa0a64`. WG15 issued no
  Git write or deployment command, but its tracked code/test state is already
  present in that externally created commit.
