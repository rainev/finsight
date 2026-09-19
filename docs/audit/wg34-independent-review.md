# WG34 independent HCA professional-liability challenge

Checked 2026-09-16 by `wg34_hca_prof_liability`, gpt-5.6-luna with high
reasoning, one bounded read-only reviewer. No edits or network access. The
primary verified every material source, economic and calculation finding.

The reviewer approves only the narrow accounting/cash-overlap guard. Period-end
professional-liability line1464M (year-end comparison1466M), narrative reserves1996M,
dedicated insurance investments519M=current117M+noncurrent402M, next-12-month
net payments573M/retained532M and ordinary NCI3433M are kept as different
economic objects. The1996M−1464M=532M equality remains an arithmetic diagnostic,
not a reported current reserve. Restricted insurance assets are not surplus
cash; coverage/retention limits are not claims; no recovery receivable or paid-
claim schedule is inferred.

The existing 100%/50%/0% noncurrent reserve sensitivity is retained and relabelled
separately from NCI. It reproduces every old scenario exactly and issues no
numeric successor. The reviewer rejected blanket reserve removal because paid-
claim and forecast-cash overlap remains unbound.

The reviewer found one hardening gap: the binding requested five annual OCF
observations but initially accepted any three. The primary changed the policy to
require exactly five and added a real four-observation fail-closed mutation. Final
independent focused run: **15 passed in 3.86s**, no remaining material economic,
lineage or calculation issue. Primary focused: **15 passed in 6.35s**. Final broad:
**781 passed**, one existing Passlib crypt deprecation warning, in247.87s.

The approval is narrow. Current/noncurrent reserve scope, actual paid claims,
recognized recoveries, exact payment timing, full forward-cash overlap and the
complete preferred/common bridge remain required. HCA stays implementation_gap;
MCK, LHX, leases, portability, HON and hardening are not waived.
