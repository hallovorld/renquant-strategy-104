# Activate the wash-sale materiality floor — the fix shipped, the switch was never set

**Date:** 2026-07-31 · `renquant-strategy-104` · closes the live half of `renquant-pipeline#223`

## Bottom line

`renquant-pipeline#223` reported *"there is no cost floor anywhere in the filter."*
**That is no longer true — and checking it first changed what this PR is.**

The floor exists on `renquant-pipeline` `main`
(`kernel/selection.py:136 resolve_wash_sale_min_material_npv`, hardened against config
typos in `bd97e2f`) `[VERIFIED — read at aa3dffb, this session]`. Its resolver
deliberately falls back to `WASH_SALE_MIN_MATERIAL_NPV_LEGACY = 0.0` and its own
docstring says *"this repo never substitutes a policy value of its own."*

**All six strategy configs left the key UNSET** `[VERIFIED — this session]`, so the
resolver returned `0.0` on every run and the pre-#223 behaviour — block on any realised
loss — stayed in force. The code was merged and dark.

This PR sets `wash_sale_min_material_npv = 1.00` in all six. **One inserted line per
file, no reformatting.**

## THIS CHANGES LIVE TRADING BEHAVIOUR

Once this config is pinned, sessions that previously placed **zero** orders will place
orders. That is the intent. It is stated here rather than buried because a config PR
that alters a capital gate should not read like a typo fix.

## Why $1.00, derived not chosen

The 2026-07-28 session's own logged NPV tax costs (7 costed blocks, **$15.21** total):

| floor | blocks released | tax forgone | % of total | % retained |
|---:|---:|---:|---:|---:|
| $0.05 | 1 | $0.04 | 0.3% | 99.7% |
| $0.10 | 3 | $0.22 | 1.4% | 98.6% |
| $0.50 | 5 | $0.88 | 5.8% | 94.2% |
| **$1.00** | **6** | **$1.59** | **10.5%** | **89.5%** |
| $2.00 | 6 | $1.59 | 10.5% | 89.5% |
| $14.00 | 7 | $15.21 | 100.0% | 0.0% |

`[VERIFIED — this session, from the filter's own logged figures quoted in pipeline#223]`

**The choice is robust, not tuned.** The next cost above $0.71 is CRWD at $13.62, so
**every** floor in `[$0.72, $13.61]` — a **19×** range — releases exactly the same 6
blocks and retains exactly the same 89.5% of protected tax. $1.00 sits inside that flat
region and is a round number a human can reason about. It is not a fitted parameter.

The single block it keeps, CRWD at **$13.62**, is **89.5% of all the tax the rule was
protecting that day** — one block doing the work of seven.

## What this does NOT fix

**`expected_dollar_return` is a second dark switch, and the more important one.**
`selection.is_wash_sale_blocked_with_cost` already accepts it and will, when supplied,
block only if the expected return is below the tax cost — the economically correct test.
`task_candidates.py:102` passes `expected_dollar_return=None` with the comment
*"μ̂ not yet known at this stage"* `[VERIFIED — this session]`, so **no live caller ever
supplies it** and the comparison never happens.

A dollar floor is a proxy for that comparison. It is strictly worse and it is what can
be turned on today. Filed separately — it needs μ̂ available at candidate time, which is
an ordering change in the pipeline, not a config value.

Also unfixed: `MU`'s *"P/L unknown — binary block"*. Unknown realised P/L still inherits
the block regardless of magnitude. Correct for a safety gate, wrong for a tax
optimisation — it converts a data gap into a capital gate. Same separate filing.

## Rollback

Delete the six inserted lines. The resolver returns `0.0` and behaviour is bit-identical
to today. No migration, no state.

---

## Review round 1 — DE-SCOPED: the live gate is no longer touched

Codex: *"this is a live capital-gate policy change, but the $1 activation is justified
only by seven realized-cost blocks from one 2026-07-28 session … it is still a chosen
policy threshold."* Accepted, and the PR is re-scoped rather than argued.

**`wash_sale_min_material_npv` is removed from `strategy_config.json` and
`strategy_config.golden.json`.** The live gate keeps the resolver's
`WASH_SALE_MIN_MATERIAL_NPV_LEGACY = 0.0`, i.e. **no behaviour change to live trading
in this PR at all.** The four shadow configs keep `1.00`.

Golden moves with live deliberately: `scripts/daily_104.sh` uses
`strategy_config.golden.json` as the drift reference for the live config, so setting
the key in one and not the other would fire the drift WARN on every run
`[VERIFIED — daily_104.sh:222, this session]`. Checked that this introduces no new
divergence: live and golden differ on exactly the same six keys before and after
(`sizing`, `walkforward`, `sleeve`, `execution`, `deployment_governor`, and one dated
note) `[VERIFIED — key-by-key diff of both files at origin/main and on this branch]`.

**Why shadow-only is the right shape rather than a retreat.** The evidence codex asks
for — released blocks and retained tax exposure across multiple completed sessions —
does not exist yet and cannot be manufactured from the one session that motivated the
threshold. The shadow lanes execute the same selection path against real candidates
and place no orders, so activating there **produces exactly that evidence** while the
live gate stays at the legacy floor. This PR stops being "turn it on" and becomes
"start generating the record that would justify turning it on".

**Promotion criteria, stated now so they cannot be chosen later.** Before
`wash_sale_min_material_npv` is set in `strategy_config.json`:

1. **≥ 4 completed shadow sessions** on distinct trading days, reporting per session
   the blocks released by the floor and the realised-loss NPV each carried;
2. an **end-to-end consumer check** that the pinned strategy config is the one the
   pipeline actually read and that the gate value took effect — not that the key is
   present in a file, which is what this PR would otherwise have proved;
3. the released set contains **no block whose NPV exceeds the floor** — a floor that
   releases something above its own threshold is not the mechanism it claims to be;
4. a **rollback trigger** written before activation: if any session releases a block
   later found to breach §1091 wash-sale treatment, the key is removed from
   `strategy_config.json` and `strategy_config.golden.json` in one commit, and the
   deployment pin reverts to the preceding strategy pin.

**Rollback for this PR as it now stands:** revert the four shadow config lines. No live
surface is touched, so there is nothing else to undo.

**What is still true and unchanged:** `renquant-pipeline#223`'s "no cost floor
anywhere" is stale — the floor exists and is hardened; all six configs left it unset so
it was dark. This PR lights it in shadow only.

## Review round 2 — the branch did not pass its own semantic-pin contract

Codex accepted the shadow-only scope, then found the branch failing
`test_shadow_blend_profile_semantic_pins`: the blend profile is contracted as
*"prod minus submission, not a fork"*, and `wash_sale_min_material_npv` was an
unregistered delta between blend and prod.

**Registered as an intentional shadow-only delta**, asserted rather than normalised
silently — `blend[key] == 1.00` and `key not in prod` — before the normalisation step.
This contract exists to make every blend-vs-prod difference deliberate, and **an
unlisted delta that merely happens to be popped is indistinguishable from one nobody
noticed.**

Three focused assertions added:

* **all four** shadow profiles carry `1.00` — not "the ones I remembered". A floor lit
  on three of four lanes produces evidence that does not describe the fourth;
* live and golden leave it **UNSET**, so a future re-activation must happen against the
  promotion criteria rather than by a config edit nothing objects to;
* live and golden **agree** about it in either direction, because `daily_104.sh` uses
  golden as the drift reference and lighting one alone fires the drift WARN every run.

`[VERIFIED — this session]` 35 pass. Load-bearing confirmed by injection: re-activating
the key in `strategy_config.json` fails **2** tests (the UNSET guard and the
live/golden agreement guard); removing it from one shadow lane fails **1**; both pass
again on restore.

**Unchanged:** the end-to-end consumer check stays a *promotion prerequisite*, not
something this config-only PR claims today. Nothing here shows the pinned config was
the one the pipeline read.
