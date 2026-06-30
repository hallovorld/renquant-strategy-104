# cash drag — raise slot counts (proposal)

STATUS:   PROPOSAL PR for Codex review on branch `fix/cash-drag-raise-slots` — NOT deployed, not merged.
WHAT:     Two integers in BOTH `strategy_config.json` + `strategy_config.golden.json` (kept identical):
          top-level `max_concurrent_positions` 8 → 12, and `rotation.panel_buy_top_n` 3 → 5.
          Nothing else: per-name (max_concentration 0.12, BULL_CALM max_position_pct 0.12), per-sector
          (max_positions_per_sector 6, max_sector_weight_pct), and Kelly `fractional` 0.30 are UNCHANGED.
WHY/DIR:  Real cash drag, measured today. After the demean-revert (#34) restored buying, a live `daily-full`
          deployed only $827 of $8,730 buying power; the live book is ~46% deployed / ~54% cash on 5-7
          positions. Root cause is NOT loose risk (the 12% per-name cap is never hit) — it is two slot caps
          plus small Kelly targets from low model mu (0.03-0.05 → f*=mu/σ² → ~3-5% per name). Raising slots
          lets the book hold MORE small positions without enlarging any one of them.
EVIDENCE: live run 2026-06-29: 6 veto survivors (FTNT/SOFI/NEE/BLK/AVGO/CVX); FTNT correlation-blocked;
          panel_buy_top_n=3 + only-3-open-slots → 3 SELECTs (SOFI/NEE/BLK), only 2 sized (BLK rounded to
          0 shares at ~$950). `[measured 2026-06-29, live book this session]`
SCOPE:    Slot counts only. Expected effect: book can hold up to 12 small positions; deployment ~46% → ~55-60%
          as candidates fill — direction/rough magnitude, NOT a guarantee (depends on veto pass-through per run).
          12/5 are a calibrated first pass for operator/Codex review, not a tuned optimum.
CAVEAT:   More deployment = more exposure to the model's picks, whose ranking currently runs roughly INVERSE to
          sell-side analyst upside (tops FTNT/SOFI which the street rates Hold; underweights BLK/AVGO rated
          Strong Buy). This cuts cash drag; it does NOT fix signal quality. Deeper lever = orthogonal/analyst
          blending (105 track), out of scope here.
TESTS:    Added `test_cash_drag_slot_counts_are_pinned_and_active_matches_golden` (pins 12/5, asserts
          active==golden, re-asserts untouched risk knobs). Ran the focused file + full suite green: 27 passed.
          System python is 3.9 and lacks deps; verified in a throwaway venv (pydantic/numpy/pandas/pyarrow/
          scipy/statsmodels/arch + eval_type_backport shim for 3.9 union syntax) with PYTHONPATH to the sibling
          renquant-common/src. CI uses 3.10 natively (no shim needed).
REVERT:   Flip the two integers back (12→8, 5→3) in both configs. No artifact/retrain/schema change.
NEXT:     Codex review of the 12/5 calibration; if approved, deploy via promote_pin (merge != live); observe
          realized deployment over a few runs and revisit the numbers.
