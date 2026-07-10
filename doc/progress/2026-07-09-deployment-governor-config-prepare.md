# D5 Deployment Governor — PREPARE config block

**Date**: 2026-07-09
**Status**: Config PREPARE (no behavior change; fully inert)

## Bottom line

Added a top-level `deployment_governor` block to all three configs with
`enabled: false` in ALL THREE (production, golden, AND shadow), per
orchestrator RFC #443 (Deployment Governor top-down sizing architecture).
The consumer — the renquant-pipeline `deployment_governor` reader (pipeline
PR #179, parallel) — defaults to false, so this block is INERT
(byte-identical behavior) until that code merges AND the pin bumps.

Codex review on PR #50 (accepted): the initial revision armed shadow
(`enabled: true`) alongside uncalibrated placeholder values — a silent
future arming, not an inert prepare. Fixed: shadow is now also false.

## S1 shadow arming = a SEPARATE dedicated future PR

Shadow arming happens only after ALL of:

1. Orchestrator RFC #443 approved
2. renquant-pipeline `deployment_governor` reader (pipeline PR #179) merged
3. D6 nested-selection tuning on the frozen tuning subset produces a frozen
   tuned config

That future arming PR flips ONLY the shadow flag and records the exact
config + artifact fingerprints.

## Schema (all values PLACEHOLDERS — not calibrated)

- `enabled` — false in all three configs
- `e_ceil_by_regime` — BULL_CALM 0.95 / BULL_VOLATILE 0.7 / CHOPPY 0.6 / BEAR 0.35
- `hysteresis_band` 0.05, `kelly_fraction` 0.3, `mu_shrinkage` 0.0,
  `top_k` 8, `max_step_per_session` 0.15

Numeric values are placeholders pending nested-selection tuning on the frozen
tuning subset (prereg protocol D6); they must NOT be treated as calibrated.

## Changes

- `configs/strategy_config.json` — `deployment_governor` block, `enabled: false`
- `configs/strategy_config.golden.json` — same, `enabled: false` (kept in
  lockstep per the active==golden semantic-match contract)
- `configs/strategy_config.shadow.json` — same, `enabled: false` (Codex
  review fix; S1 arming deferred to the dedicated future PR above)

Tests: `tests/test_strategy_configs.py` 25 passed; full suite 76 passed,
1 skipped. No test pins the top-level key set, so no test changes needed.

## Next steps

1. RFC #443 approval; renquant-pipeline reader PR #179 merges; pin bumps
2. D6 preregistered nested-selection tuning on the frozen tuning subset →
   frozen tuned config replaces placeholder values
3. Dedicated S1 shadow-arming PR (shadow flag only + recorded config/artifact
   fingerprints; shadow runs on isolated broker state alpaca_shadow)
4. Production enablement requires the D6 preregistered replay gate + S2
   canary + recorded operator sign-off (single boolean flip in a reviewed PR)
