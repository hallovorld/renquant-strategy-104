# Operator-delegated shadow-slot activation — topdecile_clf_blend_leg

**Date:** 2026-07-26 · **Executor:** claude agent, under explicit operator
delegation · **Refs:** strategy#63/#64 (rulings), model#77 (artifact),
orch#581 (readout job), pipeline#213 (frozen forward readout)

## What changed

Appended the `topdecile_clf_blend_leg` shadow entry (identity double-pinned:
`expected_content_sha256` + `expected_config_fingerprint`) to
`configs/strategy_config.json` and `configs/strategy_config.golden.json`,
and extended the pinned assertion in `tests/test_strategy_configs.py` in the
same commit. Entry content is byte-identical to the block preserved in #63's
merged progress doc (the block codex content-reviewed; #63/#64 objections
were solely about the executing party, not the content).

## Authorization trail (verbatim)

The #63/#64 rulings require an operator-executed step for protected-path
writes. The operator attempted the prepared command block twice; both
attempts were corrupted by terminal paste mangling (truncated sha256 mid-hex,
fused pytest/git arguments — the second attempt failed on
`pytest: unrecognized arguments: -A`). The operator then delegated in-session
on 2026-07-26:

> 再给我一次这个需要我跑的命令
>
> （粘贴两次均被终端截断损坏后）
>
> **我授权你帮我跑**

This delegation is specific to this prepared, content-frozen block. Commits
deliberately carry the claude identity, not the operator's, so the record
shows truthfully who typed what under whose grant.

## Safety envelope

- Shadow-only consumer: primary scorer untouched; funnel-inert until the
  pipeline#213 frozen readout (INFO @60 matured sessions, GATE @120).
- Artifact verified loadable via the PINNED runtime `PanelScorer` with valid
  probabilities before this activation.
- Revert: `git revert` of this commit; no live artifact/state is touched by
  this PR. Pin advance is a separate, separately-recorded step.
