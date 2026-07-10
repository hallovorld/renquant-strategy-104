# D5 Deployment Governor — PREPARE config block

**Date**: 2026-07-09
**Status**: Config PREPARE (no behavior change)

## Bottom line

Added a top-level `deployment_governor` block to all three configs
(production=OFF, golden=OFF, shadow=ON), per orchestrator RFC #443
(Deployment Governor top-down sizing architecture). The consumer — the
renquant-pipeline `deployment_governor` reader — is a parallel PR whose flag
defaults to false, so this block is INERT (byte-identical behavior) until
that code merges AND the pin bumps. This is the D5 step; it mirrors the
one_share_floor S1 PREPARE pattern (#49).

## Schema (all values PLACEHOLDERS — not calibrated)

- `enabled` — false in active/golden; true in shadow (S1 arming; shadow runs
  on isolated broker state `alpaca_shadow`, no live orders)
- `e_ceil_by_regime` — BULL_CALM 0.95 / BULL_VOLATILE 0.7 / CHOPPY 0.6 / BEAR 0.35
- `hysteresis_band` 0.05, `kelly_fraction` 0.3, `mu_shrinkage` 0.0,
  `top_k` 8, `max_step_per_session` 0.15

Numeric values are placeholders pending nested-selection tuning on the frozen
tuning subset (prereg protocol D6); they must NOT be treated as calibrated.

## Changes

- `configs/strategy_config.json` — `deployment_governor` block, `enabled: false`
- `configs/strategy_config.golden.json` — same, `enabled: false` (kept in
  lockstep per the active==golden semantic-match contract)
- `configs/strategy_config.shadow.json` — same, `enabled: true` (S1 shadow arming)

Tests: `tests/test_strategy_configs.py` 25 passed; full suite 76 passed,
1 skipped. No test pins the top-level key set, so no test changes needed.

## Next steps

1. renquant-pipeline reader PR merges (parallel), pin bumps → shadow starts
   producing governor telemetry
2. D6 preregistered nested-selection tuning on the frozen tuning subset →
   replace placeholder values
3. Production enablement requires the D6 preregistered replay gate + S2
   canary + recorded operator sign-off (single boolean flip in a reviewed PR)
