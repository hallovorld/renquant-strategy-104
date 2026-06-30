# cash drag — analysis record (proposal-only; fractional shares is the real lever)

STATUS:   ANALYSIS RECORD PR on branch `fix/cash-drag-raise-slots` — proposal-only, NOT a config change.
          Active/golden config is UNCHANGED (production 8/3); config diff vs main is EMPTY. Merges as the
          cash-drag decision record. Resolves Codex CHANGES_REQUESTED on PR #35 via OPTION 1 (proposal-only).
OUTCOME:  Do NOT raise slot counts in isolation. The REAL lever is FRACTIONAL SHARES (+ optional
          min-conviction floor). Slot count is secondary.
WHAT:     No config change. The earlier revision had raised top-level max_concurrent_positions 8→10 and
          rotation.panel_buy_top_n 3→4 in both configs; that is now REVERTED to the production 8/3 in both
          active and golden, so the diff vs main is docs-only. The pinning test now asserts 8/3 (was 10/4).
WHY/DIR:  Real cash drag, measured today. After the demean-revert (#34) restored buying, a live `daily-full`
          deployed only $827 of $8,730 buying power; the live book is ~46% deployed / ~54% cash on 5-7
          positions.
REPLAY:   A readonly 8/3-vs-10/4 replay run TODAY on the live book (no real orders, through the order path)
          OVERTURNED the slot-raise hypothesis:
          - 10/4 deploys only ~$427 MORE — CVX ~$169 + ZM ~$258 — barely denting ~$3.9k idle cash.
          - The marginal slot admits a LOW-CONVICTION name (ZM, conv 0.36) → confirms Codex's "admits
            lower-quality marginal names" concern with real evidence.
          - The genuinely better high-price names AVGO ($373) / BLK ($950) / GS ($1022) were SELECTED but
            bought 0 shares: each had a Kelly target ~$400 (~4%) SMALLER THAN ONE WHOLE SHARE → whole-share
            rounding floored them to 0. The binding constraint is ROUNDING on high-price names, NOT slots.
          - This contradicts the earlier DERIVED counterfactual (which guessed 10/4 adds AVGO ~$1,227); the
            derived arithmetic missed the rounding interaction — exactly the risk Codex flagged for a
            non-execution counterfactual.
LEVER:    FRACTIONAL SHARES (primary): notional/fractional sizing lets AVGO/BLK/GS fill at their small ~$400
          targets instead of rounding to 0, deploying cash into the BETTER names. MIN-CONVICTION FLOOR
          (optional): so ZM-class names don't fill slots just because they're cheap enough to round to a
          whole share. SLOT COUNT is secondary — re-measure slot pressure only AFTER fractional shares.
CODEX:    Took OPTION 1 of Codex's two clean shapes (proposal-only: revert active/golden, keep design +
          progress docs + rollback/promote criteria). Option 2 (keep 10/4 + attach replay) was attempted —
          the replay we ran for it changed the conclusion, so we keep config at 8/3. Lambda context retained:
          raising slots is the same FAMILY as the disabled qp_cash_drag_lambda=0; fractional shares deploys
          cash into the good names without re-enabling cash-drag pressure on a suspect ranking.
ROLLBACK: The pre-registered slot-raise rollback/promote criteria are retained in the design doc as the bar
          any FUTURE slot change must clear (after fractional shares lands) — NOT active here (no config
          change). Note one REVERT condition (>40% of marginal admits round to 0 sh) already trips today
          (AVGO/BLK/GS → 0), which is why slot-raise fails and fractional shares is needed first.
TESTS:    Renamed/updated `test_cash_drag_slot_counts_stay_at_production_8_3` — now pins 8/3 in both active
          and golden (was 10/4), asserts active==golden, re-asserts untouched risk knobs. Full suite green:
          27 passed. System python is 3.9 and lacks deps; verified in a throwaway venv (pydantic<3/numpy/
          pandas/pyarrow/scipy/statsmodels/arch + eval_type_backport) with PYTHONPATH=src:../renquant-common/
          src. CI uses 3.10 natively. Config diff vs main verified EMPTY.
NEXT:     Engineering: add fractional/notional order support (broker/adapter) so high-price small-target
          names fill; optionally add a min-conviction floor on new admits. Re-measure cash drag after, and
          only then revisit slot count if still bottlenecked.
