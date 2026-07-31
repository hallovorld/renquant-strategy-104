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
