# P1 one-share floor — PREPARE config keys

**Date**: 2026-07-09
**Status**: Config PREPARE (no behavior change)

## Bottom line

Added `sizing.one_share_floor_enabled` to all three configs (production=OFF,
golden=OFF, shadow=ON). Pipeline code already implemented (3 codex review
rounds, 20/20 tests, flag default OFF). This is the PREPARE step per RS-2.

## Impact estimate (07-02 data)

With floor ON, BLK ($995) and AVGO ($360) — model's #1 and #3 ranked
candidates — would deploy $1,355 additional capital. Cash drops from 65%
to ~52%. Both positions within 12% max_concentration cap.

## Changes

- `configs/strategy_config.json` — `sizing.one_share_floor_enabled: false`
- `configs/strategy_config.golden.json` — same (active==golden contract)
- `configs/strategy_config.shadow.json` — `sizing.one_share_floor_enabled: true`

## Next steps

1. Shadow runs with floor ON will produce comparison data
2. RS-2 preregistered gate: concentration, cash use, exposure metrics
3. If gate passes → enable in production config (single boolean flip)
