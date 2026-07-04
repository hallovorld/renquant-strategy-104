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

## Round 2 (review)

Codex found two real issues:

1. **`vehicle` was validated but never read.** `compute_sleeve_allocation()`
   used only `spy_fraction`/`sgov_fraction`, so `vehicle="SPY"` with
   untouched (default) fractions silently allocated zero SPY, all SGOV —
   a misleading config contract, not a docs nit. Fixed by making `vehicle`
   the real source of truth via a new `resolve_vehicle_fractions()` helper:
   `"SPY"` → 100% SPY, `"SGOV"` → 100% SGOV, `"split"` → defers to the
   explicit `spy_fraction`/`sgov_fraction` fields (the blended-ratio
   override, e.g. RS-1's 30/70 planning heuristic). Both
   `ParkingSleeveConfig.__post_init__` (for the guard below) and
   `compute_sleeve_allocation()` now resolve through the same helper, so
   they can't disagree about what a config actually means.

2. **No guardrail against a config that looks live-authorized before RS-1's
   SPY arm actually clears its preregistered gate.** Added
   `spy_arm_gate_cleared: bool = False` to `ParkingSleeveConfig`. The
   validator computes the *effective* (post-`vehicle`-resolution) SPY
   fraction and raises `ValueError` if `enabled=True and mode="live" and
   effective_spy_fraction > 0` unless `spy_arm_gate_cleared=True` is set
   explicitly. This only gates the SPY arm specifically (matching RS-1's
   own framing — SGOV is not subject to the pending gate): SGOV-only live
   configs, shadow-mode configs, and disabled configs are all unaffected.
   The one existing test constructing a legitimate live+SPY fixture
   (`test_split_allocation`) now sets the flag explicitly, acknowledging
   it's a unit test of the compute path, not a real authorization.

9 new tests added (35 total): vehicle resolution for SPY/SGOV/split, and
the guardrail's positive/negative cases (blocks live+SPY without the flag,
allows it with the flag, does not block SGOV-only/shadow/disabled). All
pass; 1 pre-existing, unrelated failure elsewhere in the repo
(`test_config_drift_cli_exposes_repo_root`, a subprocess/env artifact)
reproduces identically against a clean `origin/main` checkout — not
caused by this change.
