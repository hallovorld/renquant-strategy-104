# P0 rotation threshold calibration — design

**Date**: 2026-07-09
**Status**: Design RFC (no behavior change)

## Bottom line

`min_expected_advantage_pct=0.06` is structurally unreachable — XGB ER range
maxes at ~0.05, so no candidate can ever produce a 6% net advantage. Production
has fired 0 rotations in 7 trading days. Code default is 0.03; production
override to 0.06 has no documented rationale.

Proposes 0.06 → 0.02 with preregistered shadow protocol. This fixes portfolio
quality (rotating losers for better names) but does NOT directly reduce cash
drag. The real cash drag lever is Kelly sizing (separate P2 design).

## Changes

- `doc/design/2026-07-09-rotation-threshold-calibration.md` — full design
  with 7-day rotation tree evidence + preregistered protocol

## Context

Reprioritized per operator challenge: veto floor (A-0) DEFERRED — lowering it
admits mediocre candidates that hit the same downstream bottleneck. Rotation
threshold (P0) fixes a clear mis-calibration. Cash drag root cause is sizing
(P2), not filtering.
