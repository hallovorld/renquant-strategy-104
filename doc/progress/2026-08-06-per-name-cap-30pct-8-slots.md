# 2026-08-06 — Per-name concentration cap 12% → 30%, slots stay 8

## STATUS

Config-only change, PROPOSED. Not live until merged **and** the orchestrator pin
advances (`doc/memory/` — "merged is not deployed": the daily run reads
`strategy_config.json` from the PINNED subrepo, not from this branch).

## WHAT

Operator directive 2026-08-06, verbatim: **"单股上限可以是30%，最多保留8支股票"**
(single-name cap may be 30%, keep at most 8 names).

| knob | before | after | note |
|---|---:|---:|---|
| `regime_params.BULL_CALM.max_position_pct` | 0.12 | **0.30** | the operative per-name cap |
| `ranking.kelly_sizing.max_concentration` | 0.12 | **0.30** | INERT (`kelly_sizing.enabled=false`); moved in step so re-enabling Kelly cannot silently revert the directive |
| `max_concurrent_positions` | 8 | **8** | unchanged — already the directive's number |
| `regime_params.BULL_CALM.max_sector_weight_pct` | 0.35 | **0.35** | unchanged; 0.35 > 0.30 already leaves the new cap reachable |
| `max_positions_per_sector` | 6 | **6** | unchanged |
| `BULL_VOLATILE` / `CHOPPY` / `BEAR` | — | — | unchanged; de-risking regimes keep 0.20 / 0.15 (4 slots) / 0 |

Applied to production + golden + the six live shadow lanes
(`shadow_blend`, `shadow_blend_momentum`, `shadow_blend_momentum_fast`,
`shadow_blend_rb_fast`, `shadow_blend_rb_mom`, `shadow_momentum`) so the shadow
A/B stays a MODEL comparison. Had prod moved alone, every shadow-vs-prod delta
would have been confounded by a sizing difference.

`shadow.json` / `shadow_a.json` / `shadow_b.json` are deliberately NOT touched:
they already sit off-baseline at 0.15/0.35 and have no run DB under
`data/runs.alpaca_shadow_*` — the retired §2a arms.

## WHY-DIR

The cap and the sizing chain were never reconciled. `max_concurrent_positions=8`
was chosen assuming 12% positions (8 × 12% = 96% deployed), but the sizing chain
multiplies the regime cap by `confidence_to_size_multiplier`, so 8 slots could
only ever reach 8 × 6.84% = 55%. That single unreconciled pair produced BOTH
observed symptoms at once — a book that is simultaneously "over its position cap"
and "80% idle".

## EVIDENCE

- artifact: `configs/strategy_config.json` + 7 mirrored configs; `tests/test_strategy_configs.py`
- prod or exp: **prod config**, gated behind PR + pin advance; nothing written to a live path
- existing data: live account 2026-08-06, daily-full log `logs/daily_104/2026-08-06.log`
- best-known?: yes for the mechanism; **no** for the claim that 30% is optimal — see NOT ESTABLISHED
- scope: BULL_CALM only

Measured this session:

```
confidence_to_size_multiplier  [VERIFIED — kernel/regime.py, called directly]
  conf<=0.50 -> 0.50 (floor)        cap 0.30 -> 15.0%
  conf =0.57 -> 0.57               cap 0.30 -> 17.1%   <- live today
  conf =1.00 -> 1.00               cap 0.30 -> 30.0%
live median position                3.1% of equity     [VERIFIED — Alpaca positions API]
=> deliberate ~5.5x concentration increase at today's confidence
```

Knob precedence re-derived rather than assumed
[VERIFIED — `kernel/regime_resolver.py:50-57`]:
`regime_params.<regime>.max_position_pct` **overrides**
`position_sizing.max_position_pct`. The global 0.15 is dead under every regime
that carries an overlay, which is all four. Changing only the global would have
been a no-op.

No upper-bound validator exists on `max_position_pct`
[VERIFIED — grep over `renquant-pipeline/src`]; `kernel/sizing.py:391` checks
only `math.isfinite`. So 0.30 cannot fail-close.

Tests: **101 passed, 1 failed** — the one failure
(`test_config_drift_cli_exposes_repo_root`) is **identical on `origin/main`**
measured in a clean worktree, i.e. pre-existing and not introduced here.

## NOT ESTABLISHED

1. **That 30% is optimal.** It is an operator risk decision, implemented as
   given. No sweep, no backtest, no prereg supports the specific number.
2. **That this makes the book buy.** It changes position SIZE, not COUNT. With
   10 positions held against `max_concurrent_positions=8`, `open_slots = -2` and
   the buy path stays closed until three exits land. Today's daily-full confirms:
   `PrepareSelectionTask: no open slots`, `buys=0`.
3. **That deploying the idle capital is profitable.** Untested.
4. **Downside.** A name at the realised 17.1% losing 30% costs the book 5.1%.
   That is the risk the operator has accepted, stated so it is legible.

## NEXT

- Codex review → merge → orchestrator pin advance (orch#808) → re-run daily full.
- **Blocking the buy path independently of this PR:** `open_slots` counts filled
  positions only and is blind to in-flight accepted-unfilled buys
  (renquant-pipeline#269). That is what let the book reach 10 against a cap of 8.
- **Backtest cannot validate this change as written:**
  `portfolio_qp/wf_replay_loader.py:87-90` hardcodes
  `_MAX_POSITION_PCT_BY_REGIME = {"BULL_CALM": 0.15}`, which never matched the
  production 0.12 either. Any WF/QP replay silently sizes at 0.15. Filed
  separately.

## REVERT

Set `regime_params.BULL_CALM.max_position_pct` back to `0.12` and
`ranking.kelly_sizing.max_concentration` back to `0.12` in all eight configs
(production, golden, and the six shadow lanes listed above), restore the four
`0.12` assertions in `tests/test_strategy_configs.py`
(`test_cash_drag_slot_counts_stay_at_production_8_3`,
`test_shadow_ab_leaves_prod_and_golden_at_production_baseline`), and delete
`_max_position_pct_reason`. No other file changes.
