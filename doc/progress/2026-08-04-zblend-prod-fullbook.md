# 2026-08-04 — OPERATOR OVERRIDE: prod primary → z-blend (full book)

## Authority

Operator, repeatedly and verbatim: architecture fixed 2026-08-03 ("慢动量要进
prod的!要成为moe里的一部分!"); demanded all day 2026-08-04 ("z-blend进prod说了
一百遍了"); blast-radius choice made against a presented menu that stated the
risk plainly: **整本切换** (full-book switch, over $500/$1,000/$2,000 sleeve
options). This PR executes that directive. It is an operator override of the
preregistered GOAL-8 evidence ladder, recorded as such — NOT an evidence-based
promotion.

## What changes

`strategy_config.json` + `strategy_config.golden.json` (mirrored):
- `ranking.panel_scoring.kind` xgb → **blend**; `components` = [governance-served
  prod scorer (content pin 6461b827, RFC#210), chain-verified slow-momentum
  ledger leg] — ported from the S1 shadow profile that executed cleanly today
  (86 candidates, 2 buys, zero fail-close).
- Nine unit-dependent control groups DISABLED/NULLED with dated notes (the z
  composite has no calibrated-probability units): global_calibration,
  kelly_sizing, conviction_gate, panel buy_floor, rotation panel floors ×3,
  qp_admission_gate floors, model_sell.panel_veto.
- Score-unit-independent controls UNTOUCHED: model_protection 3-strike,
  trailing, risk budget, wash-sale NPV floor, sector caps, execution, tax.

New `configs/zblend_prod_artifact_manifest.json`: same
operator_override_directive_audit shape as the 06-23 XGB manifest (which stays
untouched as history, supersession chain asserted in tests). Positive claims
carry only what is measured; explicitly-not-claimed includes: zero OOS record,
no evidence of improvement, disabled-controls inventory. Review condition:
first of 10 sessions / −5% from switch-date equity / 2026-08-31 retrospective.

## Rollback

Single-commit config revert + pin revert: component[0] IS the prior prod
scorer, so rollback restores the exact pre-switch logic with no artifact swap.

## Verification

- s104 suite: 97 passed / 1 skipped / 1 pre-existing env failure (identical on
  clean main). Five semantic guards deliberately updated to the new contract
  with dated override notes; the xgb→zblend manifest supersession chain is now
  itself pinned by test.
- Readonly FULL-FUNNEL sim against this exact config (live-bridge,
  readonly-alpaca) run pre-merge; result recorded in the PR thread.

## Fleet note (operator directive, same message)

prod = zblend(reversal+slow-mom) is step 1 of the operator's fleet
architecture (shadow variants: revblend+slow / rev+fast / revblend+fast; all
lanes z-blend-based MoE). The fleet is registered as its own goal in
renquant-orchestrator; fast-momentum variants stay dormant until the first
fast artifact (2026-08-08).
