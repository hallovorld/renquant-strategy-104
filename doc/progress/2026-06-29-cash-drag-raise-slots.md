# cash drag — staged slot raise (proposal)

STATUS:   PROPOSAL PR for Codex review on branch `fix/cash-drag-raise-slots` — NOT deployed, not merged.
          Revised after Codex CHANGES_REQUESTED: STAGED 10/4, downgraded from the original 12/5.
WHAT:     Two integers in BOTH `strategy_config.json` + `strategy_config.golden.json` (kept identical):
          top-level `max_concurrent_positions` 8 → 10, and `rotation.panel_buy_top_n` 3 → 4.
          Nothing else: per-name (max_concentration 0.12, BULL_CALM max_position_pct 0.12), per-sector
          (max_positions_per_sector 6, max_sector_weight_pct), Kelly `fractional` 0.30, and the CHOPPY
          regime override max_concurrent_positions=4 are UNCHANGED.
WHY/DIR:  Real cash drag, measured today. After the demean-revert (#34) restored buying, a live `daily-full`
          deployed only $827 of $8,730 buying power; the live book is ~46% deployed / ~54% cash on 5-7
          positions. Root cause is NOT loose risk (the 12% per-name cap is never hit) — it is two slot caps
          plus small Kelly targets from low model mu (0.03-0.05 → f*=mu/σ² → ~3-5% per name). Raising slots
          lets the book hold MORE small positions without enlarging any one of them.
STAGED:   Codex's CHANGES_REQUESTED was VALID: 12/5 was one-snapshot arithmetic and is the same family of
          knob as the disabled qp_cash_drag_lambda=0 cash-deployment-pressure safeguard (raises total
          exposure to a ranking the PR itself calls suspect). So 12/5 was downgraded to a STAGED FIRST STEP
          10/4, with a single-day counterfactual, head-on lambda-conflict acknowledgement, pre-registered
          rollback/promote criteria, and an honest validation-status statement. "Per-name risk unchanged" is
          explicitly NOT claimed to be a sufficient safety argument.
COUNTERFACTUAL (DERIVED from stored 2026-06-29 scores + selection logic; NOT a fresh exec / full QP replay):
          6 veto survivors (FTNT/SOFI/NEE/BLK/AVGO/CVX); FTNT correlation-blocked → 5 admissible, book held 5.
          8/3:  3 open slots, top_n 3 → SELECT SOFI/NEE/BLK; AVGO hit "slots full"; BLK rounds to 0 sh ($950
                vs ~$400 target) → sized SOFI $473 + NEE $354 = ~$827.
          10/4: 5 open slots, top_n 4 → adds AVGO (rank #4); BLK still rounds to 0 → ~SOFI+NEE+AVGO ≈ $1,227.
          12/5: would further add CVX (rank #5).
          CRITICAL (analyst cross-check, not P&L): the marginal slots admit STREET-BETTER names — AVGO
          (Strong Buy, ~+35-40% to target) and CVX (Buy, +13%) are higher-rated than SOFI (street Hold)
          which 8/3 already buys. So the extra slots admit street-BETTER names, not junk — on this one date.
LAMBDA:   Acknowledged head-on: raising slots IS a cash-deployment-pressure knob in the same family as the
          disabled qp_cash_drag_lambda=0; total exposure to the suspect ranking rises. Mitigants: staged
          small (10/4); every strict admission gate UNCHANGED and still binding (WF gate, conviction mu_floor,
          rank veto mean+1σ, correlation, sector, min-edge, wash-sale, share-rounding); hard rollback.
ROLLBACK (pre-registered, first-pass): revert 10/4→8/3 if ANY of — deployment doesn't rise ≥+5pp over N=10
          fresh-feed days; slot-4+ names trail first-3 by >−2.0pp benchmark-relative; rounding/slippage waste
          >30bps of marginal $ or >40% of marginal admits round to 0 sh; gross >75% BP or drawdown <−8% or any
          cap breached. PROMOTE 10/4→12/5 ONLY after the ledger shows slot-4+ names are NOT net-negative
          benchmark-relative (mean ≥0, not worse than first-3) and no revert condition trips.
VALIDATION STATUS (honest): the decision-ledger is too short for multi-day validation — clean fresh-feed live
          data only began 2026-06-29. This is a STAGED, reversible first step to be validated via the ledger
          as it accrues (~Aug 2026 for 60d), NOT a validated optimum. It does NOT fix signal quality (model
          ranking runs ~inverse to sell-side; orthogonal-signal blend is the 105 track).
TESTS:    Updated `test_cash_drag_slot_counts_are_pinned_and_active_matches_golden` (pins 10/4 now, asserts
          active==golden, re-asserts untouched risk knobs). Ran the focused file + full suite green: 27 passed.
          System python is 3.9 and lacks deps; verified in a throwaway venv (pydantic<3/numpy/pandas/pyarrow/
          scipy/statsmodels/arch + eval_type_backport) with PYTHONPATH=src:../renquant-common/src. CI uses
          3.10 natively.
REVERT:   Flip the two integers back (10→8, 4→3) in both configs. No artifact/retrain/schema change.
NEXT:     Codex review of the staged 10/4 step; if approved, deploy via promote_pin (merge != live); observe
          realized deployment + the pre-registered metrics over fresh-feed days; promote to 12/5 only on
          ledger evidence per §5.
