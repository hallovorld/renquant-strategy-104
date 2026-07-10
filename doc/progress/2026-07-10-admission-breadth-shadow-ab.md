# Admission-breadth shadow A/B — preregistration + shadow config flip

**Date**: 2026-07-10
**Status**: Preregistered shadow A/B armed (shadow-only; zero live behavior change)

## Bottom line

Registered the admission-breadth A/B
(`doc/design/2026-07-10-admission-breadth-shadow-ab.md`) and flipped the
shadow config to the treatment arm: `ranking.panel_scoring.buy_floor`
`adaptive_quantile → adaptive_mean_std`, `buy_floor_std_mult 1 → 0.5`
(floor = max(0.20, mean + 0.5σ) on calibrated rank_score). Production and
golden stay at `adaptive_mean_std` / 1.0σ — untouched and now pinned by test.

Why: `deployable ≤ breadth × cap`; the cap-grid run (orchestrator
`design/deployment-governor-rfc`,
`doc/research/evidence/cap_grid_tuning/results.md`) showed cap-raising is
dominated (−8.2% net for +18pp deployment, 2× single-name loss tail), so
post-veto breadth is the primary deployment lever; the prod 1.0σ veto killed
~75-86% of scored candidates (06-23 → 07-09, hypothesis-generation only).
Veto arms cannot be replayed (sim DB lacks pre-veto candidates — orchestrator
#443 D6 §2 Phase-2 amendment), hence live shadow.

Successor to CLOSED #47; its three Codex blockers are fixed in the design
(§8): future-only evaluation (no same-window selection), a preregistered
forward-return quality estimand for marginal entrants (plus a prod-XGB
counterfactual to control the PatchTST-shadow scorer confound), and
hypothesis-level language (0.5σ = candidate treatment, not an optimum).

## Protocol highlights (frozen at merge)

- ≥ 10 future-only shadow sessions before any verdict; mid-run changes void
  the run; one declared +10-session extension allowed.
- Estimands: end-of-chain deployed fraction (with within-arm marginal-entrant
  weight decomposition for attribution) + 20d/60d SPY-relative forward return
  of marginal entrants vs incumbent admits (HAC inference).
- Non-degradation gates: 12% per-name cap unchanged, 35% sector cap,
  turnover ≤ 2× paired prod session, shadow MDD ≤ 0.30; breach = stop + REJECT.
- Verdict = recommendation memo; live enablement = SEPARATE gated PR
  (pre-registration + codex review). Rollback = revert one config flip;
  isolated `alpaca_shadow` state, zero live orders.

## Changes

- `configs/strategy_config.shadow.json` — treatment arm flip (3 lines);
  supersedes the 2026-06-11 `adaptive_quantile(0.8)` setting (no recorded
  verdict; `buy_floor_quantile` retained, inert in mean_std mode).
- `doc/design/2026-07-10-admission-breadth-shadow-ab.md` — preregistration.
- `tests/test_strategy_configs.py` — pin test (prod/golden 1.0σ baseline;
  shadow 0.5σ treatment).

Tests: `tests/test_strategy_configs.py` 26 passed.

## Next steps

1. Merge (codex review); evaluation clock starts at the first post-merge
   shadow session.
2. After ≥ 10 sessions: recommendation memo (verdict), including the prod-XGB
   counterfactual marginal-set analysis.
3. Any live enablement: separate PR + pre-registration gate + codex review.
