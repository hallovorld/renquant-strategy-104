# per-ticker retrain timeout — durable fix (no-buys root cause)

STATUS:   CONFIG CHANGE on branch `fix/per-ticker-retrain-timeout`. Raises
          `parallel_ticker_timeout_seconds` 600 -> 2400 in both active
          (`strategy_config.json`) and golden (`strategy_config.golden.json`).
          Implements Phase-1 / Pillar-2 of the merged `model-freshness-governance`
          design. Suite green: 27 passed.
OUTCOME:  The per-ticker tournament retrain gets 40min (was 10min) — comfortably
          covers the full 142-ticker RL+RF+XGB tournament so it stops timing out
          and silently failing.
ROOT:     `scripts/train_104.py --skip-panel` (the per-ticker tournament retrain
          over 142 tickers) TIMED OUT under the 600s (10min) cap: only ~67/142
          tickers finished in 600s -> `ParallelTimeoutError` -> the whole retrain
          FAILED SILENTLY -> per-ticker models never refreshed -> the universe
          staleness gate then dropped every non-held ticker -> 0 buy candidates.
          This is the recurring no-buys root cause diagnosed 2026-06-30.
EVIDENCE: 2026-06-30 the retrain was manually worked around with a side config at
          timeout 3600 — all 142 tickers finished in ~493s. Measured full-tournament
          wall time sits in the ~493-1280s band; 2400s gives ~2x headroom over the
          worst measured run without masking a genuinely hung worker.
WHY 2400: 40min is a comfortable ceiling above the measured ~493-1280s tournament
          (roughly 2x the slowest observed), leaving room for a slow data day / cold
          cache while still failing fast on a real hang. Not set to 3600 (the manual
          workaround value) to avoid over-generous masking; 2400 is the tuned durable
          value.
SCOPE:    Changed ONLY the timeout key (+ an adjacent `_`-prefixed provenance note).
          No other config value touched — slot counts, mu_floor, kelly, risk knobs,
          panel/scorer contracts all unchanged.
LOCKSTEP: `test_active_and_golden_semantic_config_match` requires active and golden
          to agree on every non-`_` key, so the bump is applied to BOTH production
          policy files. The provenance note is a `_`-prefixed key and is stripped
          before that comparison, so it does not perturb the contract.
SHADOW:   `strategy_config.shadow.json` (readonly PatchTST panel-scoring shadow) is
          intentionally left at 600 — it carries no CI contract on this key and the
          production per-ticker tournament reads the active config; out of scope here.
TESTS:    `PYTHONPATH=src:../renquant-common/src <RenQuant .venv py3.10> -m pytest -q`
          -> 27 passed (incl. `test_active_and_golden_semantic_config_match`,
          `test_cash_drag_slot_counts_stay_at_production_8_3`,
          `test_config_drift.py`). JSON re-validated with `python -m json.tool`.
