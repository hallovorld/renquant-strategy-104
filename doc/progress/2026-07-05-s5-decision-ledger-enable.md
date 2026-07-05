# Enable S5 decision-ledger verdict persistence

DATE: 2026-07-05
PR: (this PR)
STATUS: feat

## What

Added `decision_ledger.enabled: true` to all three strategy configs
(active, golden, shadow). The pipeline's `DecisionLedgerWriteTask`
(renquant-pipeline #176) writes gate verdicts to
`~/renquant-data/decision_ledger.db` via orchestrator modules. This is the
final enablement step for S5 — all code was already merged across
orchestrator (#133 GateRegistry + decision_ledger) and pipeline (#175/#176
formatter + task wiring).

## Safety

- Fail-open: if orchestrator modules are unavailable, logs WARNING and
  continues the daily run. S5 is a measurement substrate, not a trading gate.
- Verdict-only: per-ticker decisions are formatted but NOT persisted from this
  task (the outcome_observer handles those separately to avoid partial-write
  poisoning — see task_decision_ledger.py module docstring).
- Not a gate change — no trading behavior affected.
