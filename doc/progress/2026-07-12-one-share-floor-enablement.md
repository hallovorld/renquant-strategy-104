# One-share floor — enablement contract (flag OFF, pending prerequisites)

**Date**: 2026-07-12
**Feature**: `sizing.one_share_floor_enabled`
**PR**: strategy-104#55 (`config/operator-enablement-batch-1`)
**Status**: OFF. This document stages the monitoring contract and kill rule
so they are reviewed and merged BEFORE the flag is flipped. Enablement
requires the prerequisites below.

## Enablement prerequisites

1. **Producer implementation**: pipeline#191 defines the sizing-intent
   record but does NOT emit these metrics, assemble a daily run bundle, or
   implement their calculations. Required before enablement:
   - **Pipeline producer**: a pipeline task that computes and persists the 8
     metrics below from the decision ledger on each run (new pipeline PR).
   - **Orchestrator scorecard integration**: orchestrator must read the
     persisted metrics into the immutable daily run bundle and surface them
     in the daily-full scorecard (new orchestrator PR).
   - **End-to-end evidence**: at least one production dry-run with
     `floor=OFF` that proves the full pipeline→bundle→scorecard chain emits
     all 8 counters with correct values (verified against manual ledger
     replay).
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
| `floor_impl_cost_est` | see Implementation Cost definition below | cost monitoring (estimate only — NOT a realized-cost metric) |

### Implementation cost definition (`floor_impl_cost_est`)

This is an **estimate**, not a realized cost. It uses the fill record, not
post-trade reconciliation:

- **Inputs**: order fill price (from broker fill event), NBBO midpoint at
  order submission time (from market data snapshot), order quantity (always
  1 share for floor rescues).
- **Formula**: `impl_cost = qty × (fill_price − mid_at_submission)` for
  buys. Aggregated as `sum(impl_cost)` across all floor-rescued fills in
  the session.
- **Fee source**: broker commission schedule (Alpaca: $0 equity commissions;
  if this changes, add per-fill commission from broker fill event).
- **Limitations**: does not capture market impact (1-share orders have
  negligible impact) or opportunity cost. Does not decompose by spread vs
  slippage. The estimate is sufficient for the cost monitoring purpose; the
  kill rule's PnL threshold (below) uses a separate, realized-PnL
  definition.

### PnL attribution contract (for kill-rule evaluation)

The "cost-adjusted loss" and "negative returns" kill rules require a
reproducible PnL definition:

- **Entry price**: broker fill price from the floor-rescue order fill event.
- **Observation horizon**: mark-to-market at session close (for the
  next-day return metric) and realized at exit fill price (for the
  cumulative PnL metric). Both are tracked; the kill rules specify which
  applies.
- **Price source**: broker fill prices for realized; closing price from
  market data provider (same source as the daily pipeline) for
  mark-to-market. Timestamp: fill timestamp for entry, 16:00 ET close for
  mark-to-market.
- **Corporate actions**: adjusted via the same corporate-action handler the
  pipeline uses for price history (split-adjusted fill price at the time of
  the action, carried forward).
- **Partial-exit allocation**: FIFO lot matching (consistent with the
  existing wash-sale and tax accounting). If a floor-rescued lot is
  partially sold, PnL is attributed to the sold quantity at FIFO cost
  basis.
- **Non-floor coexistence**: if a ticker has both a floor-rescued lot and a
  prior non-floor lot, the floor lot is tracked separately by entry
  timestamp and lot identifier. PnL from the non-floor lot is excluded from
  floor metrics.

### Prospective comparator (pre-registered)

**Baseline comparator**: the pre-enablement period (floor OFF) is
historical context only, not a prospective control. The prospective
comparator for the enablement decision:

- **Shadow/control pairing**: not available (the armed shadow instrument
  runs floor=ON in both arms; a proper control requires a separate
  floor=OFF shadow, which is not currently implemented).
- **Prospective single-arm analysis window**: first 20 enabled sessions.
  Metrics: mean `floor_rescued_notional` per session, mean
  `floor_impl_cost_est`, floor-rescued position next-day return
  distribution.
- **Eligibility denominator**: sessions where `floor_eligible_count > 0`
  (sessions with no eligible candidates are excluded from rescue-rate and
  cost calculations, included in cash% tracking).
- **Missing data / invalid session policy**: if the daily run bundle is
  missing or the producer reports an error for any of the 8 counters, that
  session is excluded from the analysis window and the 20-session count
  does not advance. Three consecutive missing sessions triggers an
  investigation (not a kill).
- **Decision at window close**: at session 20, review the full metrics
  against the kill-rule thresholds. If no kill rule has fired, the floor
  remains ON. If any kill rule fires within the window, the floor is
  disabled immediately per the kill rule below (do not wait for session 20).

## Kill / rollback rule

**Owner**: operator (config change) + codex review (PR approval).
**Mechanism**: flip `sizing.one_share_floor_enabled` back to `false`.

| Trigger | Threshold | Window |
|---------|-----------|--------|
| Concentration breach | any `max_position_pct_actual > 0.12` (hard cap) | single session |
| Excess deployment | cumulative `floor_rescued_notional > 20% PV` in any rolling 5-session window | 5 sessions |
| Cost-adjusted loss | floor-rescued positions' cumulative realized PnL (FIFO exit fill price − entry fill price, per lot, summed) < −$500 net of broker commissions | 10 sessions |
| Data integrity | `floor_eligible_count` or `floor_rescued_count` disagree with the decision ledger by >0 | single session |
| Model degradation | floor rescues consistently (≥3 consecutive eligible sessions) produce negative next-session-close mark-to-market return (close-on-day-after-entry / entry-fill-price − 1 < 0 for median rescue) | 3 sessions |

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
