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
| Broker-side GTC stop limitation documented and accepted | operator | Assumption only |
| Stage-3 shadow packet: fractional sizing in shadow mode with monitoring | orchestrator | Not started |
| Software stops pager SLA demonstrated | orchestrator PR #481 | Merged (dark template) |
| Dead-process at-risk-notional bound measured (see §Dead-process below) | orchestrator | Not measured |
| Fractional stop coverage invariant proven (see §Coverage below) | orchestrator + execution | Not implemented |
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

## Fractional stop coverage invariant

`is_armed()` alone is insufficient — a parseable registry can be armed with
zero entries, and a start-of-session check says nothing about fractional
buys opened later in the session.

**Coverage metric** (computed at every post-order and heartbeat boundary):

```
fractional_stop_coverage = registered_fresh_fractional_stop_notional
                         / gross_fractional_position_notional
```

Where:
- Numerator: sum of notional for fractional positions that have a
  corresponding software-stop registry entry with `is_armed() == True`
  AND staleness < `max_staleness_minutes`, reconciled against broker
  holdings (not just the decision ledger).
- Denominator: sum of notional for all fractional positions from the
  broker portfolio snapshot.

**Hard gates**:
- A new fractional buy is blocked unless `fractional_stop_coverage == 1.0`
  AFTER the hypothetical addition (i.e., the stop for the new position
  must be registered before the buy order is submitted).
- Any `fractional_stop_coverage < 1.0` at a heartbeat boundary → kill
  trigger (disable fractional entries immediately, create immutable
  integrity incident).
- Unknown/uncovered fractional positions (in broker holdings but not in
  the registry) → hard gate: no new fractional buys until reconciled.

## Monitoring contract (for future enablement)

When enabled, the following metrics are tracked daily. Ownership:
**renquant-execution** owns normalized broker order/fill/reject events;
**renquant-pipeline** owns fractional intent/decision facts from the
decision ledger; **renquant-orchestrator** joins their immutable records
into the daily run bundle and surfaces them in the scorecard.

| Metric | Definition | Owner | Threshold |
|---|---|---|---|
| `fractional_order_count` | count of orders submitted with fractional quantity (qty has non-zero decimal part), per session | execution | > 0 (liveness) |
| `fractional_fill_rate` | filled fractional orders / submitted fractional orders. Terminal states: filled, partially_filled (counted as filled), canceled, rejected, expired. Pending/new excluded from denominator. Rolling 5-session window. | execution | > 95% over 5 sessions |
| `fractional_notional_total` | sum of (fill_price × fill_qty) for all fractional fills in the session. Source: broker fill events. Currency: USD. | execution | < 10% PV |
| `non_fractionable_reject_count` | count of orders rejected with "not fractionable" reason code | execution | = 0 |
| `fractional_stop_coverage` | see §Coverage above | orchestrator | = 1.0 |
| `stop_staleness_minutes` | max heartbeat age across all fractional-position stops | orchestrator | < max_staleness_minutes |

### Missing/errored data policy

**Safety-critical metrics** (`fractional_stop_coverage`, `stop_staleness_minutes`,
`non_fractionable_reject_count`): missing or errored data is a **fail-closed
event** — block new fractional entries for the next session and create an
immutable integrity incident in the run bundle. These metrics cannot be
excluded from evaluation because their absence is itself the safety failure
the gate exists to detect.

**Descriptive/monitoring metrics** (`fractional_order_count`,
`fractional_fill_rate`, `fractional_notional_total`): missing or errored
data → session excluded from threshold evaluation, flagged for
investigation. Three consecutive missing sessions → investigation (not a
kill, but a hold on new fractional entries until resolved).

## Dead-process at-risk-notional bound

The previous "4% PV" statement conflated notional exposure (dollars) with
time (latency). These are separate quantities:

### What is being bounded: at-risk notional

The decision is: **how much fractional notional is unprotected during a
dead-process window?** This is a notional quantity (USD), not a loss
estimate.

- **At-risk notional** = `gross_fractional_position_notional ×
  (1 − fractional_stop_coverage)` at any point in time. With the coverage
  invariant above enforced, this should be 0 at all heartbeat boundaries
  — but can be nonzero transiently between a buy fill and the next
  registry stamp.
- **Transient exposure window** = time between a fractional buy fill and
  the registry stamp that covers it. Measured over a 20-session shadow
  window as `P99(fill_to_stamp_latency)`.
- **Kill threshold**: at-risk notional > 5% PV at any heartbeat boundary
  (not transient — the transient window is bounded by the fill-to-stamp
  latency, which is measured but not independently kill-gated).

### What is NOT bounded here

A financial-loss estimate under a dead-process scenario requires an
adverse-move model (historical stress distribution, gap risk, confidence
level, horizon). This contract does NOT produce a loss bound — it produces
a notional-exposure bound. A loss estimate is a separate analysis
(orchestrator research scope) that must be completed before the operator
risk sign-off, using the measured at-risk notional as an input alongside
a preregistered adverse-move distribution.

## Kill/rollback rule

| Trigger | Action |
|---|---|
| Any fractional order rejected with "not fractionable" | Disable immediately, add symbol to `non_fractionable_tickers` |
| `fractional_fill_rate` < 95% over 5 sessions | Disable + investigate broker connectivity |
| `fractional_stop_coverage` < 1.0 at any heartbeat boundary | Disable immediately + immutable integrity incident |
| At-risk notional > 5% PV at any heartbeat boundary | Disable + incident review |
| Safety-critical metric missing/errored | Block new fractional entries next session |
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
