# WG14 ordinary and redeemable NCI carrying claims

Verified 2026-09-11; user confirmation pending. This is a bounded working-group
result, not release approval. Production, scheduling, merge, push, deployment,
later batches and family adapters were untouched.

## Retained mechanism

APD and CMI were retained as two model-appropriate treatments of positive
current NCI. APD uses a parent-equity residual-income model, so current NCI is a
reconciliation diagnostic rather than a second deduction. CMI uses enterprise
FCFF, so current NCI belongs in the ownership bridge once; guarantees and an
unconsolidated VIE remain separate economic objects.

APD's versioned rule requires the current undimensioned NCI total, the
dimensioned consolidated-VIE subset, total equity, parent equity, the matching
NCI equity member and current NCI-attributable earnings. It proves $16.5964B
total equity - $2.7126B NCI = $13.8838B parent equity. The $1.8316B VIE amount
is a subset of total NCI and is not added. NCI investments, distributions,
redemptions/purchases and OCI/income flows remain source rows, not balances.

CMI's versioned rule binds $1.059B ordinary NCI but fails closed on two separate
objects. The filing reports a $257M guarantee carrying value and a $50M guarantee
maximum; their unequal amounts prove they are not one additive/nettable scope.
The unconsolidated Amplify VIE has a $350M investment, $412M contributed and
$418M future contribution without a timed payment schedule. None is added to
NCI, preferred equity or debt.

## Five-company result

| Company | Classification | Previous low / base / high | Current low / base / high |
|---|---|---|---|
| APD | Retained representative; $2.7126B NCI with $1.8316B consolidated-VIE subset, parent-equity model | 40.751018411317126 / 68.53958889346042 / 103.3782018277093 | 42.031886443398164 / 69.07202315107281 / 101.7752119366412 |
| CMI | Retained difficult case; $1.059B ordinary NCI plus separate guarantee/VIE surfaces | 65.62106314103318 / 235.41395352983125 / 444.9462166832929 | No candidate; explicit financial review |
| BAX | Negative $27M ordinary NCI; $105M contingent/separation claims are separate | 0 / 8.54935871774756 / 27.122993321184648 | No candidate; implementation gap preserved |
| BLDR | No NCI/redeemable/temporary claim; authorized-only preferred negative control | 21.781785084149906 / 72.40667125273195 / 181.61927313845578 | No candidate; unrelated bridge review preserved |
| DOV | No NCI carrying balance; generic “before NCI” income concepts are not claims | 63.881665069820805 / 101.42695915123933 / 157.86702955732756 | No candidate; unrelated bridge review preserved |

APD changes are +1.2808680320810382 / +0.5324342576123939 /
-1.6029898910681055 per share (+3.1431558817811567% /
+0.7768273288595529% / -1.5506072486535016%). The current source locks one
$62.31508078994614 book-value-per-share anchor across scenarios instead of the
legacy share-sensitivity-derived $60.41610832750685 / $61.83473169540922 /
$63.2965618663949 anchors. The NCI treatment itself remains zero additional
deduction because the model starts from parent equity.

BAX's current negative NCI is not inverted into common value; its current $10M
contingent consideration, $43M separation indemnification and $52M disposal-
group contingent liability require a separate claim stack. BLDR and DOV were not
converted into carrying-claim companies merely because generic income concepts
contain the words “noncontrolling interest.”

## Verification evidence

- APD controlling filing: accession `0000002969-26-000036`, period
  `2026-06-30`; structural SHA-256
  `dd25d5f8ec2620005fb510bd596b430f0cf7c7370171017404a4c353cf503da2`;
  raw filing SHA-256
  `ff85a4c2fb4d7bbbbb6956cc82ca96214088e8040bb00e452007f9263cbfdd27`.
- CMI controlling filing: accession `0000026172-26-000029`, period
  `2026-06-30`; structural SHA-256
  `aff549544795c851d904926833b947e0a2d3660607417f63eb474203999056d6`;
  raw filing SHA-256
  `c44944a4872fac516bbf0a614044120c82e0e0c27845eb487a25d73dbd580bb8`.
- Five-company direct source report:
  `output/us-refresh-runtime/source-validation/b6f738a27ebf13a0b98a239687bb4d78eb5b7f23bb326c67c80c579cf881d74c/report.json`,
  SHA-256 `b6f738a27ebf13a0b98a239687bb4d78eb5b7f23bb326c67c80c579cf881d74c`.
- Frozen two-worker retained group:
  `output/us-refresh-group-verification/c79c33246eef8c72c2dafa776cff849311918d15e2b39407bfcf7127d4e34242/report.json`,
  SHA-256 `330b363354ec4f6e5676049c72c9a25cc18e16c1bab45b680e46db4770913d60`.
  Outcome: one source-bound candidate and one exact source/economic review.
- Focused regression: 154 passed; one unrelated dependency deprecation warning.
- Isolated APD API/database UAT:
  `output/us-refresh-operational-uat-20260910T164735Z-986af6f6/uat-report.json`,
  SHA-256 `d3f684496fa83379525691f58b2e30f12e9dfa2f3b85899a1380495fa000c5b9`.
  The first attempt stopped because Docker was not running. After the local
  database runtime became healthy, a fresh real FastAPI worker served the
  predecessor/candidate/rollback values, reloaded without restart, rejected
  stale CAS and preserved 440 companies plus 419 private recipes. Production
  was not touched.
- Work register: `output/us-refresh-work-register.json`, SHA-256
  `830c23b1af5b72c8b78b41f16a355125cc88211b789b9396239d2d9029f6d2a6`.
  Counts: 263 compiled contracts, 156 implementation gaps, one current-policy
  source-bound result and zero explicit successive-period proofs.

Two Luna xhigh reviewers independently inspected APD/BAX and BLDR/CMI. The
primary agent separately inspected DOV, integrated and verified the APD/CMI
ownership rules, and reran the real source calculations and runtime path.

## Remaining blockers

- CMI requires contract-level reconciliation of its $257M carrying guarantee
  and $50M maximum, plus exact timing for the $418M future Amplify contribution.
- BAX needs its negative NCI diagnostic separated from $105M of current
  contingent and separation claims without carrying the prior $133M maximum.
- BLDR and DOV have no current NCI claim, but their separate cash/debt/securities
  bridge gaps remain required work.
- No company has successive-period proof under the current release candidate.
