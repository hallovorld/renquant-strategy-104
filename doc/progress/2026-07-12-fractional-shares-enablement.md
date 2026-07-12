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
| Broker `broker_fractional_contract` adapter methods | renquant-execution | Not implemented |
| Broker-side GTC stop limitation documented and accepted | operator | Assumption only (2% PV bound not measured) |
| Stage-3 shadow packet: fractional sizing in shadow mode with monitoring | orchestrator | Not started |
| Software stops pager SLA demonstrated | orchestrator PR #481 | Dark template staged |
| Dead-process exposure bound measured (not assumed) | orchestrator | Not measured |
| Explicit signed-off risk decision with evidence | operator | Pending above |

## Monitoring contract (for future enablement)

When enabled, the following metrics should be tracked daily:

| Metric | Source | Threshold |
|---|---|---|
| fractional_order_count | execution log | > 0 (liveness) |
| fractional_fill_rate | execution log | > 95% |
| fractional_notional_total | execution log | < 10% PV |
| non_fractionable_reject_count | execution log | = 0 |
| software_stops_armed | orchestrator scorecard | must be true |
| stop_staleness_minutes | orchestrator scorecard | < max_staleness_minutes |

## Kill/rollback rule

| Trigger | Action |
|---|---|
| Any fractional order rejected by broker | Disable immediately |
| software_stops not armed | Disable (prerequisite violated) |
| Dead-process exposure > 4% PV | Disable + incident review |
| Operator request | Disable (flip boolean) |

## Rollback

Set `execution.fractional_shares.enabled = false` in strategy_config.json and
strategy_config.golden.json. Existing fractional positions close at next rotation
via whole-share path.
