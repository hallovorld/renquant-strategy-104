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
| Fractional stop coverage invariant proven (see §Invariant 1 below) | orchestrator + execution | Not implemented |
| Fractional gross notional cap enforced (see §Invariant 2 below) | orchestrator + pipeline | Not implemented |
| Execution liveness chain demonstrated (see §Invariant 2 below) | orchestrator | Not measured |
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

## Protection invariants

Fractional position protection requires two independent invariants:
**state coverage** (data plane — are the stop records complete?) and
**execution liveness** (control plane — is a process alive to act on
them?). Coverage == 1.0 does not imply liveness: the registry can be
complete, parseable, and within its staleness budget while no process is
evaluating or submitting the stop exit.

### Invariant 1: State coverage

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

### Invariant 2: Execution liveness

State coverage cannot establish a dead-process exposure bound because the
registry remains 1.0 when the evaluator dies. Protection requires a
running process that periodically evaluates stop conditions and submits
exit orders. **Execution liveness** measures whether that process is alive.

**Liveness chain** (each link must be demonstrated):
1. **Last successful evaluation** — timestamp of the most recent
   heartbeat where the evaluator checked stop conditions AND confirmed
   connectivity to the broker (not just registry read).
2. **Stale detection** — an independent watchdog (launchd heartbeat or
   external monitor) detects that the evaluator has not checked in within
   `max_staleness_minutes`. Detection latency = watchdog interval.
3. **Page delivery** — ntfy/pager notification sent. Delivery latency
   measured from watchdog trigger to delivery confirmation.
4. **Acknowledgement** — operator acknowledges the page.
5. **Recovery/manual flatten** — operator either restarts the evaluator or
   manually flattens fractional positions via broker.

**Execution liveness exposure:** During the interval from step 1 to step
5, every gross fractional holding whose protection requires the loop is at
risk. The exposure is:
```
liveness_exposure = gross_fractional_notional_at_last_eval / PV
```
This is bounded NOT by the coverage metric (which is 1.0 throughout) but
by an independent **fractional gross notional cap**:
```
gross_fractional_notional <= fractional_gross_cap_pct × PV
```
The cap limits how much fractional exposure CAN exist, and therefore how
much is at risk during a dead-process window regardless of coverage state.

**Relationship between the two invariants:**
- State coverage gates individual orders: no buy without a registered
  stop.
- The gross cap gates aggregate exposure: total fractional notional
  cannot exceed the cap.
- Together they bound dead-process risk: at most `fractional_gross_cap_pct
  × PV` is at risk, all of which has a registered stop (coverage == 1.0),
  but no process is acting on the stops until recovery.

**What the threshold caps:** The precommitted bound caps gross at-risk
notional (USD). It does NOT cap outage duration (time, bounded by the
liveness chain latencies) or financial loss (requires an adverse-move
model, see §Dead-process below). The threshold is enforceable because
the gross cap is a hard gate on fractional buys, not a post-hoc
measurement.

### Buy/stop lifecycle

A stop cannot be irrevocably registered for a position that may not fill.
The lifecycle has three states:

1. **Pending/reservation:** Before a fractional buy order is submitted,
   a stop reservation record is created in the registry with status
   `PENDING`. The reservation is included in coverage calculations as
   if the position existed (i.e., coverage must be 1.0 including the
   pending stop before the buy order is submitted).
2. **Fill-confirmed/active:** On receiving a fill event from the broker,
   the stop record transitions to `ACTIVE` with the actual fill price
   and quantity. The stop trigger level is set based on the fill price.
   The fill timestamp is recorded for `fill_to_stamp_latency`
   measurement.
3. **Cancelled/reconciled:** On reject, cancel, or expiry of the buy
   order, the pending reservation is removed from the registry. On
   partial fill, the reservation is split: filled portion transitions
   to ACTIVE, unfilled portion is cancelled. On position exit (sell
   fill), the stop record is archived with exit timestamp and reason.

**Reconciliation:** At each heartbeat, the registry is reconciled against
broker holdings. Any ACTIVE stop without a corresponding broker position
→ archive (position was sold externally or by another path). Any broker
fractional position without an ACTIVE stop → coverage violation → kill
trigger (Invariant 1). Any PENDING stop older than
`max_pending_age_minutes` without a fill → cancel + investigate.

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
| `fractional_stop_coverage` | see §Invariant 1 above | orchestrator | = 1.0 |
| `stop_staleness_minutes` | max heartbeat age across all fractional-position stops | orchestrator | < max_staleness_minutes |
| `gross_fractional_notional_pct` | gross_fractional_notional / PV. Source: broker portfolio snapshot. | orchestrator | <= fractional_gross_cap_pct |
| `evaluator_last_heartbeat_age` | minutes since last successful evaluator heartbeat (stop evaluation + broker connectivity confirmed) | orchestrator | < max_staleness_minutes |

### Missing/errored data policy

**Safety-critical metrics** (`fractional_stop_coverage`, `stop_staleness_minutes`,
`non_fractionable_reject_count`, `gross_fractional_notional_pct`,
`evaluator_last_heartbeat_age`): missing or errored data is a **fail-closed
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

### What is being bounded

During a dead-process window, state coverage (Invariant 1) remains 1.0 —
the registry is intact but no process is evaluating or submitting stops.
The at-risk quantity is bounded by **Invariant 2 (execution liveness)**,
specifically the fractional gross notional cap:

- **At-risk notional** = `gross_fractional_notional` at the time the
  evaluator dies. Bounded by `fractional_gross_cap_pct × PV` (the hard
  cap from Invariant 2).
- **Kill threshold**: `gross_fractional_notional > fractional_gross_cap_pct
  × PV` at any heartbeat boundary → block new fractional buys.
  `fractional_gross_cap_pct` is set at enablement (proposed: 5% PV) and
  is enforceable because it is a pre-order gate, not a post-hoc
  measurement.
- **Transient coverage gap** = time between a fractional buy fill and the
  stop reservation transitioning from PENDING to ACTIVE. Measured over a
  20-session shadow window as `P99(fill_to_stamp_latency)`. This is a
  data-plane latency bounded by the buy/stop lifecycle (§above), not the
  dead-process scenario.

### Outage duration (separate quantity)

The dead-process outage duration is bounded by the liveness chain
(Invariant 2): `last_eval → stale_detection → page_delivery → ack →
recovery`. Each link's latency is measured during the 20-session shadow
window. The total outage P99 is the sum of the chain's P99 latencies.
This is a time quantity (minutes), not a notional quantity.

### What is NOT bounded here

A financial-loss estimate under a dead-process scenario requires:
1. The at-risk notional (bounded above by the gross cap)
2. The outage duration (bounded above by the liveness chain)
3. An adverse-move model: historical stress distribution, gap risk,
   confidence level, and horizon over the outage duration

This contract produces bounds (1) and (2). Bound (3) — the loss
estimate — is a separate analysis (orchestrator research scope) that must
be completed before the operator risk sign-off, using (1) and (2) as
inputs alongside a preregistered adverse-move distribution.

## Kill/rollback rule

| Trigger | Action |
|---|---|
| Any fractional order rejected with "not fractionable" | Disable immediately, add symbol to `non_fractionable_tickers` |
| `fractional_fill_rate` < 95% over 5 sessions | Disable + investigate broker connectivity |
| `fractional_stop_coverage` < 1.0 at any heartbeat boundary | Disable immediately + immutable integrity incident |
| `gross_fractional_notional_pct` > `fractional_gross_cap_pct` | Disable + block new fractional buys until below cap |
| `evaluator_last_heartbeat_age` > `max_staleness_minutes` | Independent watchdog pages operator; disable new fractional entries |
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
