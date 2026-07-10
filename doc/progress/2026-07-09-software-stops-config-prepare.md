# S-FRAC v2 stage-3 software stops — PREPARE config block (default OFF)

**Date**: 2026-07-09
**Status**: Config PREPARE (no behavior change; `enabled=false` everywhere)

## Bottom line

Declared the software-stops arming contract in policy: added
`execution.software_stops` to all three configs with `enabled: false`.
Consumer is the merged, wired, UNARMED registry in renquant-pipeline
(`src/renquant_pipeline/software_stops.py`); per D7 (orchestrator #444) the
S-FRAC v2 stage-3 fractional arming requires this key to exist in strategy
config. Inert while false.

## Verified reader contract (do-not-invent-keys check)

`SoftwareStopRegistry.from_config` reads exactly:

- `execution.software_stops.enabled` — absent/false => `from_config` returns
  `None` => the layer does not exist; stage-0 semantics untouched (byte-inert).
- `execution.software_stops.registry_path` — default
  `data/rq105/software_stops.json` (broker-tagged by `registry_path_for`,
  e.g. `software_stops.alpaca.json`).
- `execution.software_stops.max_staleness_minutes` — default `30.0`
  (heartbeat budget for `check_software_stops_liveness.py`).

`is_armed()` (the probe `commit_contract.software_stops_armed` calls) returns
`not self._corrupt` — i.e. armed only when the layer is enabled (registry
constructed at all) AND the persisted registry loaded cleanly; a corrupt
registry fail-closes new fractional BUYs.

Declared values mirror the reader defaults exactly, so this block changes
nothing even after arming beyond making the contract explicit. Verified by
loading each edited config through the actual pipeline reader:
`from_config` returns `None` on all three (inert), and a counterfactual
`enabled=true` copy constructs an armed registry at the declared
broker-tagged path with the declared staleness budget.

## Changes

- `configs/strategy_config.json` — `execution.software_stops`
  (`enabled: false`, defaults declared, provenance `_comment`)
- `configs/strategy_config.golden.json` — same (active==golden
  semantic-match contract)
- `configs/strategy_config.shadow.json` — same, `enabled: false` INCLUDING
  shadow: arming a live protection layer is a safety act, not a shadow
  experiment (same reasoning as deployment_governor PR #50)

## Tests

`tests/test_strategy_configs.py`: 25 passed. Full suite: 76 passed,
1 skipped.

## Next steps (arming = separate future PR)

Arming (`enabled: true`) is gated on:

1. the stage-3 shadow packet,
2. pager SLA demonstration (loop-dead watchdog / liveness page actually
   reaches the operator in time), and
3. recorded operator sign-off of the machine-death risk assumption
   (a software stop dies with the machine; broker GTC stops do not).
