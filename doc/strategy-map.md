# Strategy map — what renquant-104 is optimizing, measured state, and the signal roster

STATUS: POINTER document (deliberately). Canonical sources live in renquant-orchestrator
(the control-panel repo) and are linked per section; this file states WHAT APPLIES TO THIS
STRATEGY and where the living version is. Do NOT copy numbers into here by hand — the
hand-maintained-snapshot rot of umbrella `doc/arch/strategy-104.md` (stale within weeks,
broke a design round) is the disease this format avoids.
DATE: 2026-07-02

## 1. The objective this strategy serves

```
Book = β(FLOOR: parking sleeve + ops discipline)
     + Active: IR = TC × IC_combined × √BR_eff
     + EXEC (entry/exit implementation gain) − LEAK (process failures)
```

Target G* (end-2028): total Sharpe ≥ 0.7 · net alpha ≥ 0 · max DD ≤ 15% · institutional
process. Canonical: orchestrator `doc/design/2026-07-02-unified-107-master-plan.md` (§0
state vector; re-measured monthly) and `doc/research/2026-07-02-ic-ceiling-institutional-
gap-107-route.md` (bounds, gates, fallback ladder).

## 2. Measured state (WHERE to read it, not a copy)

The weekly KPI scorecard (deployed fraction, floor gap vs SPY, gate-verdict age, ledger
coverage, PIT accrual, collector liveness, sign-laundered count, buy-side TC) is generated
by orchestrator `scripts/kpi_scorecard.py` into
`doc/research/evidence/kpi_scorecards/kpi_<date>.json`. That JSON is the truth; this doc
intentionally carries no numbers.

## 3. The signal roster (what this strategy scores with, present and planned)

- **Live primary**: XGB `panel-ltr.alpha158_fund` (operator-directed 2026-06-23; no standing
  WF verdict — repair + first verdict tracked as D1). Shadow: HF PatchTST.
- **Planned stack (pre-registered)**: orchestrator
  `doc/design/2026-07-02-m-sig-signal-stack-spec.md` — C1 estimate-revision drift (PIT store
  accruing since 2026-07-02), C2 quality composite (FMP annual, coverage-delta-gated), C3
  regime-conditioned residual momentum, C4 trend-scanning label. Thresholds frozen there;
  policy/threshold ADOPTION lands HERE (configs/) when a candidate clears its bar.
- **Closed (do not re-pitch)**: raw momentum, fundmom, label neutralization, multi-horizon
  sleeves, insider, macro frames — see orchestrator/umbrella failed-experiments records.

## 4. Policy knobs THIS repo owns (the #210 ownership split)

`configs/strategy_config.json`: conviction floor (mu_floor 0.03 — uncertainty-haircut
design M3 pending), `panel_buy_top_n` (3; A-2 widening deferred behind D1-or-M3),
`qp_cash_drag_lambda` (0; A-1 confirmed a production no-op mechanically — #240),
regime params (BULL_CALM cap 0.12, reserves), `model_staleness_days`, wash-sale/anti-churn.
Sleeve policy (β-budgeted SPY/SGOV split formula) adopts here when S7 lands — decision
memo: orchestrator `doc/research/2026-07-02-rs1-parking-sleeve.md`.

## 5. Change protocol

Signal/policy changes reach this repo ONLY through: frozen prereg (orchestrator) →
measurement on the S5/S8 substrate → design PR here citing the evidence → config PR.
Direct config edits without that chain are the anti-pattern this map exists to prevent.
