# S7: parking-sleeve config + shadow allocation

Date: 2026-07-04
Task: S7 (unified plan #231, Term FLOOR)
Design: doc/research/2026-07-02-rs1-parking-sleeve.md (RS-1 PROVISIONAL)

## What shipped

- `src/renquant_strategy_104/parking_sleeve.py` — config schema
  (`ParkingSleeveConfig`) + allocation compute + shadow log formatter
- `tests/test_parking_sleeve.py` — 26 tests covering config validation,
  allocation logic (disabled/bear/split/cap/reserve/rounding), shadow log

## Key design choices

- **Default-OFF**: `enabled=False`, `mode="shadow"`, `spy_fraction=0.0`
- **SPY arm gated**: RS-1 says PROVISIONAL — spy_fraction defaults to 0.0
  (all SGOV) until a preregistered gate clears the SPY arm
- **BEAR sweep**: all-cash in BEAR regimes by default
- **Never trades**: this module COMPUTES allocations only — execution is
  a separate, gated concern
- **Whole-share rounding**: `math.floor` (never over-allocate)

## Not in scope

- Strategy config JSON key addition (separate PR — config keys are a
  shared surface)
- Execution wiring (umbrella commit path)
- Live-mode authorization file + preregistered gate
