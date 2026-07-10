# A-0 VetoWeakBuys floor calibration — design

**Date**: 2026-07-09
**Status**: Design RFC (no behavior change)

## Bottom line

Design PR for recalibrating VetoWeakBuys `buy_floor_std_mult` from 1.0 to 0.5,
the single largest cash-drag constraint (kills 80% of candidates). Includes
preregistered shadow A/B protocol per RS-2.

## Changes

- `doc/design/2026-07-09-a0-veto-floor-calibration.md` — full design + evidence
  + preregistered protocol

## Context

VetoWeakBuys adaptive floor was set for XGB-era score distributions. PatchTST's
compressed [0.45, 0.65] range makes mean+1σ≈0.575 too aggressive — it rejects
candidates with positive calibrated expected returns. See orchestrator
`doc/research/2026-07-09-cash-drag-binding-constraints-update.md` (PR #442).
