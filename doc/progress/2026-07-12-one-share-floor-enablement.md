# One-share floor — enablement contract (flag OFF, pending prerequisites)

**Date**: 2026-07-12
**Feature**: `sizing.one_share_floor_enabled`
**PR**: strategy-104#55 (`config/operator-enablement-batch-1`)
**Status**: OFF. This document stages the monitoring contract and kill rule
so they are reviewed and merged BEFORE the flag is flipped. Enablement
requires the prerequisites below.

## Enablement prerequisites

1. **Monitoring wiring**: pipeline#191 merged and producing the counters
   below in the daily run bundle (not just a contract definition).
2. **Operator authorization**: a separately-filed, independently-verifiable
   enablement PR that flips the boolean, references this contract, and is
   approved through the normal review gate.

## Feature

One-share floor — a candidate that zeroes out ONLY because of whole-share
rounding rounds UP to 1 share iff (a) 1 share <=
`regime.max_position_pct * PV` and (b) 1 share <= investable headroom.

**Evidence basis**: sealed retrospective replay of production decision
ledger (orchestrator `doc/research/2026-07-11-enablement-evidence-floor-stops-fractional.md`
§2.3, r3 — fingerprinted, content-addressed, independently reproducible):
- 6 of 11 unambiguous canonical live sessions rescued
- Rescue range: $392.13 to $1,356.18 per session
- Mean rescue: $911.13 (~8.5% PV)
- Zero admission displacement: every eligible canonical run has `n_buys == 0`
  (floor rescues, not displaces)
- Max single-name rescue: 9.3% PV (< 12% `max_concentration` cap)
- Post-rescue cash: 52–80% (from 65–84% baseline)

**Gate status**: the evidence packet is retrospective exploratory replay,
not an RS-2 §A-3 preregistered shadow gate. The armed shadow instrument is
structurally unable to satisfy RS-2 as written (scorer mismatch).
Enablement requires the monitoring wiring and authorization prerequisites
above.

## Monitoring contract (daily, from first enabled session)

The following counters are extracted from the production decision ledger on
each market day and recorded in the daily run bundle:

| Metric | Source | Purpose |
|--------|--------|---------|
| `floor_eligible_count` | candidates with model conviction but zero whole-share allocation | denominator for rescue rate |
| `floor_rescued_count` | candidates actually rounded up to 1 share | numerator |
| `floor_rescued_notional` | sum of 1-share notional deployed by the floor | cash deployment attributable to the floor |
| `floor_rejected_cap_count` | candidates eligible but rejected by `max_position_pct` cap | cap-binding frequency |
| `floor_rejected_headroom_count` | candidates eligible but rejected by headroom constraint | headroom saturation frequency |
| `total_cash_pct` | portfolio cash / PV after all orders | cash drag trend |
| `max_position_pct_actual` | max single-position weight post-floor | concentration check |
| `floor_impl_cost_est` | estimated spread + slippage on floor orders (2× typical bid-ask for small-cap, 1× for large-cap) | realized cost tracking |

**Baseline comparator**: pre-enablement cash% trajectory (11 canonical
sessions with floor OFF, documented in the sealed replay).

## Kill / rollback rule

**Owner**: operator (config change) + codex review (PR approval).
**Mechanism**: flip `sizing.one_share_floor_enabled` back to `false`.

| Trigger | Threshold | Window |
|---------|-----------|--------|
| Concentration breach | any `max_position_pct_actual > 0.12` (hard cap) | single session |
| Excess deployment | cumulative `floor_rescued_notional > 20% PV` in any rolling 5-session window | 5 sessions |
| Cost-adjusted loss | floor-rescued positions' realized PnL < −$500 net of fees | 10 sessions |
| Data integrity | `floor_eligible_count` or `floor_rescued_count` disagree with the decision ledger by >0 | single session |
| Model degradation | floor rescues consistently (≥3 consecutive) produce negative next-day returns | 3 sessions |

On any trigger: immediately flip the flag to `false`, file a PR with the
evidence, and notify the operator. The kill is a config change (same
mechanism as enablement), not a code change.

## Verification

- Pipeline implementation: 3 codex review rounds, 20/20 tests
  (`renquant-pipeline doc/2026-07-02-one-share-floor-initiation.md`)
- Config semantic-match: `active == golden` contract preserved
- Shadow experiment arm: both arms carry `floor=ON`, so the §2a
  arm-vs-arm estimand is unaffected by this production baseline update
- Full config suite + repo suite green
