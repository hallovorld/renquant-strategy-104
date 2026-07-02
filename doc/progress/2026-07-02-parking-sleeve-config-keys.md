# parking-sleeve config keys — S7 companion (inert, enabled=false)

STATUS:   CONFIG-ONLY change on branch `feat/sleeve-config-keys`. Defines the
          top-level `sleeve` section consumed by renquant-pipeline #157
          (`ParkingSleeveShadowTask`) in all three policy files:
          `strategy_config.json`, `strategy_config.golden.json`,
          `strategy_config.shadow.json`. Every value mirrors the pipeline's
          safe defaults, and `enabled=false`, so behavior is UNCHANGED.
OUTCOME:  The S7 parking-sleeve contract (RS-1 decision memo r2 + 104
          capability program §1.3 / P1-2, both merged in renquant-orchestrator)
          is now declared in policy instead of living only in the pipeline's
          `config.get` fallbacks. Turning the shadow ON later is a one-boolean
          flip that the operator can audit here, not a code change.
KEYS:     sleeve.enabled=false, mode="shadow", spy_symbol="SPY",
          sgov_symbol="SGOV", reserve_pv_pct=0.05, beta_max=0.6, beta_pos=1.0,
          min_trade_notional=50.0, dd_budget_pct=0.15,
          log_path="logs/parking_sleeve_shadow.jsonl" — exactly the key list
          published in renquant-pipeline PR #157's "Config keys for the
          strategy-104 follow-up PR" table. #157 pins byte-inertness when the
          section is absent/disabled, so defining the keys with the same
          values is a no-op by construction.
SGOV:     NOT added to the watchlist, deliberately. Inspection: the strategy
          repo owns no standalone price-feed symbol list — daily price
          coverage is derived in the UMBRELLA (adapters/runner+sim_price:
          watchlist + sector_etf_map values + benchmark + held; LEAN main.py
          AddEquity's the benchmark_sleeve ticker only when that sleeve is
          enabled). The watchlist is the ALPHA universe (panel scoring,
          per-ticker tournament, cross-sectional admission stats); a T-bill
          ETF does not belong in it. Follow-up (umbrella, before or with any
          sleeve enable): subscribe/fetch `sleeve.spy_symbol`/`sleeve.sgov_symbol`
          when `sleeve.enabled`, mirroring the benchmark_sleeve precedent.
          Until then #157's shadow tolerates SGOV absence (logs qty=null,
          SGOV leg tracked at cost) — SPY is already in the watchlist.
SCOPE:    ONLY the new `sleeve` section (+ its `_comment` provenance) and one
          new pinning test. No existing key touched — slot counts, mu_floor,
          kelly, risk knobs, panel/scorer contracts all unchanged.
LOCKSTEP: `test_active_and_golden_semantic_config_match` requires active and
          golden to agree on every non-`_` key, so the section is added to
          BOTH production policy files with identical values. Mirrored into
          `strategy_config.shadow.json` per the optional-section house
          pattern (`bear_defensive_sleeve` precedent — its pin test iterates
          all three files, and the new sleeve test does the same).
TESTS:    `tests/test_strategy_configs.py::test_parking_sleeve_keys_are_explicit_inert_and_shadow_only`
          pins: enabled=false, mode=shadow, every numeric/string key at the
          #157 default, RS-1 cited in `_comment`, SPY in / SGOV NOT in the
          watchlist (pins the coverage decision). Full suite green — see PR.
