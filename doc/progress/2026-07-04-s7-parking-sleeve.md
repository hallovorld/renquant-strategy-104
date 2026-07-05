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

## Round 3 (review)

Codex flagged one real design hole: `max_sleeve_pct` is documented and
tested like a cap on total sleeve exposure, but `compute_sleeve_allocation`
took only `cash_available`/`portfolio_value` — no input for sleeve value
already held from prior sessions. The function could cap *this call's* new
deployment but had no way to know (or bound) cumulative exposure once
called repeatedly across sessions once execution wiring exists; the
allocation primitive would hand later integration a false sense of
protection.

Fixed via Option 1 (extend the API, not narrow the docs): added
`current_sleeve_value: float = 0.0` to `compute_sleeve_allocation()`,
representing sleeve notional already held from prior sessions (0.0 =
cold start, preserves existing single-call behavior). The cap now
computes `headroom = max(0, portfolio_value * max_sleeve_pct -
current_sleeve_value)` and limits new deployment to that headroom, so
`max_sleeve_pct` binds on cumulative exposure, not a single call in
isolation. A new `sweep_reason="sleeve_cap_reached"` distinguishes
"the cross-session cap is already exhausted" from the pre-existing
`"insufficient_deployable"` (low cash / reserve floor). `sleeve_pct` on
the returned `SleeveAllocation` now reports TOTAL post-allocation sleeve
fraction (`current_sleeve_value + this session's deployment`), not just
this session's incremental share, matching the field's natural reading.

4 new tests added (39 total), including a 3-session simulation
(`test_repeated_sessions_never_exceed_cumulative_cap`) that threads each
session's deployed notional forward as the next call's
`current_sleeve_value` and asserts cumulative exposure never exceeds the
configured cap even though each session independently sees a large
`cash_available` — the exact repeated-session gap codex described.
Verified all 4 new tests genuinely fail pre-fix
(`TypeError: unexpected keyword argument 'current_sleeve_value'`) by
stashing only the source change and running them against the prior
signature — they cannot even be expressed without the fix, which is the
literal shape of the finding. Full suite: 76 passed, 1 pre-existing
skip (unrelated, same skip as round 2).

Not addressed in this round (separate, later concern): `shadow_log_entry`
does not yet log the `current_sleeve_value` a caller assumed — left out
of scope since execution wiring (which will own tracking real sleeve
state) does not exist yet; flag if this needs closing when that wiring
lands.
