# Per-name concentration cap 12% -> 30%, slots stay 8 — operator directive, deployment blocked   (PR #94)

STATUS:   in-progress — config change authored and test-covered; deployment
          authority is PARTIALLY resolved, not merge-ready. This PR writes
          `configs/strategy_config.json` directly (plus the golden config and six
          live shadow lanes), which `doc/memory/long-term-agreements.md` item 2
          marks read-only in normal PR flow. Codex's 2026-08-06 16:08 review treats
          the operator's verbatim directive quoted in this PR's description
          ("单股上限可以是30%，最多保留8支股票") as resolving the deployment-authority
          blocker on this thread, scoped narrowly: BULL_CALM per-name cap 0.30;
          `max_concurrent_positions` stays 8; BULL_VOLATILE/CHOPPY/BEAR caps, sector
          caps, max positions per sector, turnover, cash, and exit controls
          unchanged. That is not yet the durable audit record the control contract
          requires: the companion LONG-memory row
          (`long-term-agreements.md` item 2a, renquant-orchestrator#883) that would
          make this a documented exception per SOP-L is itself blocked pending a
          direct @renhao countersignature comment on that PR thread — still absent
          as of this revision. This PR should not merge until #883 lands with that
          countersignature — see NEXT. This revision does not touch any of the
          eight production-path config files.

WHAT:     Operator directive 2026-08-06, verbatim: **"单股上限可以是30%，最多保留8支股票"**
          (single-name cap may be 30%, keep at most 8 names). Raises
          `regime_params.BULL_CALM.max_position_pct` 0.12 -> 0.30 and the currently
          inert (`kelly_sizing.enabled=false`) `ranking.kelly_sizing.max_concentration`
          0.12 -> 0.30, in `configs/strategy_config.json`,
          `strategy_config.golden.json`, and the six live shadow lanes
          (`shadow_blend`, `shadow_blend_momentum`, `shadow_blend_momentum_fast`,
          `shadow_blend_rb_fast`, `shadow_blend_rb_mom`, `shadow_momentum`) so the
          shadow A/B stays a model comparison rather than being confounded by a
          sizing difference. `max_concurrent_positions` stays 8 in every regime;
          `max_sector_weight_pct` stays 0.35 (already > 0.30, so the new cap is
          reachable without a sector relaxation). `shadow.json` / `shadow_a.json` /
          `shadow_b.json` are deliberately untouched — retired arms, already
          off-baseline, no run DB.

WHY/DIR:  The per-name cap and the sizing chain were never reconciled:
          `max_concurrent_positions=8` assumed 12% positions (8x12%=96% deployed),
          but the sizing chain multiplies the regime cap by
          `confidence_to_size_multiplier`, so 8 slots could only ever reach
          8x6.84%=55%. That single unreconciled pair produced both observed
          symptoms at once — a book simultaneously "over its position cap" and
          "80% idle".

EVIDENCE:
artifact:      `configs/strategy_config.json` + golden + 6 shadow configs;
               `tests/test_strategy_configs.py`
prod or exp:   **prod config, and this PR's diff is a live write to it right now** —
               `configs/strategy_config.json:236-237` is modified on this branch.
               A prior revision of this doc said "nothing written to a live path";
               that was wrong and is corrected here per Codex's review. The
               nuance that remains true: the change is not yet SERVED — "merged is
               not deployed", the daily run reads `strategy_config.json` from the
               orchestrator's PINNED subrepo commit, not this branch — but the file
               write itself is the exact class of change
               `long-term-agreements.md` item 2 forbids in normal PR flow, which is
               why Codex blocked it regardless of the pin-advance gap.
existing data: live account 2026-08-06, daily-full log
               `logs/daily_104/2026-08-06.log`. `confidence_to_size_multiplier`
               measured directly against `kernel/regime.py`
               [VERIFIED — this session]: conf<=0.50 -> 0.50 floor (cap 0.30 ->
               15.0%), conf=0.57 -> 0.57 (cap 0.30 -> 17.1%, live today), conf=1.00
               -> 1.00 (cap 0.30 -> 30.0%); live median position 3.1% of equity
               [VERIFIED — Alpaca positions API]. Knob precedence re-derived
               [VERIFIED — `kernel/regime_resolver.py:50-57`]: the regime overlay
               overrides the global `position_sizing.max_position_pct` in all four
               regimes, so editing only the global would have been a silent no-op.
               No upper-bound validator exists on `max_position_pct`
               [VERIFIED — grep over `renquant-pipeline/src`]: `kernel/sizing.py:391`
               checks only `math.isfinite`, so 0.30 cannot fail-close.
best-known?:   yes for the mechanism (cap precedence, sizing-chain math); no for
               "30% is optimal" — an operator risk decision implemented as given,
               with no sweep or backtest behind the specific number.
scope:         BULL_CALM only; this is a prod config diff sitting in an agent PR,
               not yet an approved deployment — see STATUS.

          Tests: 101 passed, 1 failed (`test_config_drift_cli_exposes_repo_root`),
          confirmed identical on `origin/main` in a clean worktree — pre-existing,
          not introduced here.

NEXT:     Land the operator countersignature comment on
          renquant-orchestrator#883 ("单股上限可以是30%，最多保留8支股票"), which un-voids
          LONG row 2a and gives this PR's config write a durable, auditable
          exception record under `long-term-agreements.md` item 2. Once #883 merges
          with that row live, this PR is compliant with the control contract by its
          own escape hatch (SOP-L) rather than in spite of it, and can go to an
          operator merge decision. Independently: `open_slots` counts filled
          positions only and is blind to in-flight accepted-unfilled buys
          (renquant-pipeline#269) — that is what let the book reach 10 against a cap
          of 8. `portfolio_qp/wf_replay_loader.py:87-90` hardcodes
          `_MAX_POSITION_PCT_BY_REGIME = {"BULL_CALM": 0.15}`, so no WF/QP replay can
          validate this change as written (filed separately).

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

## REVERT

Set `regime_params.BULL_CALM.max_position_pct` back to `0.12` and
`ranking.kelly_sizing.max_concentration` back to `0.12` in all eight configs
(production, golden, and the six shadow lanes listed above), restore the four
`0.12` assertions in `tests/test_strategy_configs.py`
(`test_cash_drag_slot_counts_stay_at_production_8_3`,
`test_shadow_ab_leaves_prod_and_golden_at_production_baseline`), and delete
`_max_position_pct_reason`. No other file changes.
