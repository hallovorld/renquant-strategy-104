# Fractional Shares Enablement Contract

Status: OFF. This document stages the enablement contract and prerequisites for
`execution.fractional_shares.enabled` so they exist as a durable reference before
the flag is flipped.

## Feature

S-FRAC v2 fractional sizing (renquant-pipeline #153): when enabled, the pipeline
sizes positions in fractional shares instead of whole-share rounding. Eliminates
the whole-share rounding zero-out that strands capital in high-price names (e.g.
AVGO $360 rounds to 0 shares at small PV). Config keys staged in
strategy-104 PR #54 (2026-07-07 cash-drag phase-1).

## Enablement prerequisites

| Prerequisite | Owner | Status |
|---|---|---|
| Broker fractional contract (see §Broker below) | renquant-execution | Not implemented |
| Broker-side GTC stop limitation documented and accepted | operator | Assumption only (2% PV bound not measured) |
| Stage-3 shadow packet: fractional sizing in shadow mode with monitoring | orchestrator | Not started |
| Software stops pager SLA demonstrated | orchestrator PR #481 | Dark template staged |
| Dead-process exposure bound measured (see §Time-at-risk below) | orchestrator | Not measured |
| Explicit signed-off risk decision with evidence | operator | Pending above |

## Broker contract prerequisite

Before enablement, the broker adapter must demonstrate:

- **Supported symbols**: which tickers in the 104 universe support
  fractional orders (Alpaca: most US equities; a definitive list from the
  broker's `GET /v2/assets` with `fractionable=true` must be captured and
  reconciled against the universe).
- **Fractional buy behavior**: order type (market/limit), TIF restrictions
  (Alpaca fractional = DAY-only, no GTC), minimum notional ($1 Alpaca),
  quantity precision (up to 9 decimal places Alpaca).
- **Fractional sell/liquidation behavior**: whether a fractional residual
  (e.g. 0.37 shares) can be sold as a single fractional market order,
  whether partial fills apply, and the handling of odd lots below the
  broker's minimum notional.
- **Rejection taxonomy**: the set of possible rejection reasons for
  fractional orders (insufficient buying power, symbol not fractionable,
  below minimum notional, market closed for fractional, etc.) and how each
  maps to the adapter's error model.
- **Test environment**: a paper-trading or sandbox execution of at least
  10 fractional buy + sell round-trips across 3+ symbols, with fill
  records, to prove the adapter correctly handles the above. Evidence
  object: the fill log with order IDs, quantities, prices, and
  rejection/error events.

## Monitoring contract (for future enablement)

When enabled, the following metrics are tracked daily and persisted in the
immutable daily run bundle (orchestrator scorecard integration required
before enablement):

| Metric | Definition | Threshold |
|---|---|---|
| `fractional_order_count` | count of orders submitted with fractional quantity (qty has non-zero decimal part), per session | > 0 (liveness) |
| `fractional_fill_rate` | filled fractional orders / submitted fractional orders, where terminal states are: filled, partially_filled (counted as filled), canceled, rejected, expired. Pending/new orders excluded from denominator. Evaluated over a rolling 5-session window. | > 95% over 5 sessions |
| `fractional_notional_total` | sum of (fill_price × fill_qty) for all fractional fills in the session, from broker fill events. Currency: USD. Timestamp: fill event timestamp. | < 10% PV (PV from portfolio snapshot at session start) |
| `non_fractionable_reject_count` | count of orders rejected specifically because the symbol is not fractionable (rejection reason code from broker adapter) | = 0 |
| `software_stops_armed` | orchestrator scorecard: whether the software-stop registry exists, parses, and has `is_armed() == True` at session start | must be true |
| `stop_staleness_minutes` | max age of the software-stop registry heartbeat at session start, from `registry.last_updated` vs current time | < max_staleness_minutes (config) |

Metrics are produced by a pipeline task (new PR required) that reads the
broker fill/order log and the decision ledger, and are consumed by the
orchestrator's immutable daily run bundle. Missing or errored metrics for
any counter in a session → that session excluded from threshold evaluation
and flagged for investigation.

## Time-at-risk measurement (dead-process exposure bound)

The static `software_stops_armed=true` flag does not establish a
machine-death exposure bound. The following measurements are required
before enablement:

- **Protected fractional notional**: at each loop heartbeat, the sum of
  fractional position notional that has an active software stop registered
  (registry entry exists AND `is_armed()` AND staleness < max). This is
  the "protected" portion; the complement is "unprotected."
- **Heartbeat age distribution**: over a minimum 20-session observation
  window (shadow or paper), the distribution of time between consecutive
  successful heartbeat stamps. P99 heartbeat gap = the worst-case detection
  delay.
- **Watchdog detection + page delivery + acknowledgement**: from the pager
  SLA drill (orchestrator PR #481), the measured end-to-end latency from
  missed heartbeat to operator acknowledgement.
- **Aggregated bound**: `unprotected_fractional_notional / PV` at the P99
  heartbeat gap, combined with the measured page-to-ack latency, produces
  the actual time-at-risk. The 4% PV kill-rule threshold is evaluated
  against this measured bound, not the assumed 2% from the original
  enablement attempt.

## Kill/rollback rule

| Trigger | Action |
|---|---|
| Any fractional order rejected by broker with "not fractionable" | Disable immediately, add symbol to `non_fractionable_tickers` |
| `fractional_fill_rate` < 95% over 5 sessions | Disable + investigate broker connectivity |
| `software_stops_armed` false at session start | Disable (prerequisite violated) |
| Measured dead-process exposure > 4% PV | Disable + incident review |
| Operator request | Disable (flip boolean) |

## Rollback procedure

Set `execution.fractional_shares.enabled = false` in strategy_config.json
and strategy_config.golden.json. This disables new fractional sizing intent
— all future orders use whole-share rounding.

**Existing fractional inventory**: disabling the flag stops new fractional
entries but does NOT automatically liquidate existing fractional positions.
A fractional residual (e.g. 0.37 shares) cannot be represented by the
whole-share order path. Rollback procedure for existing fractional
holdings:

1. **Immediate**: flag flip stops new fractional entries. Existing
   fractional positions remain held (no forced liquidation).
2. **Escalation**: operator reviews the fractional inventory
   (`portfolio.fractional_positions()` from broker API) and decides per
   position: hold to next natural exit signal, or manually liquidate.
3. **Manual liquidation** (if chosen): submit fractional sell orders
   directly via broker adapter using the fractional order path (which
   remains functional in the adapter even when the sizing flag is OFF —
   the flag controls sizing intent, not order-type capability). Order
   type: market, TIF: DAY, quantity: exact fractional holding.
4. **Reconciliation**: after all fractional residuals are closed, verify
   portfolio contains only whole-share positions.

Until the broker adapter's fractional liquidation path is tested (see
Broker Contract above), rollback is: "disable new entries, escalate
existing fractional inventory to operator for manual resolution."
