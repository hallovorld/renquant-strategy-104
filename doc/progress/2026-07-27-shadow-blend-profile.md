# 2026-07-27 — strategy_config.shadow_blend.json: the blend full-funnel shadow profile

STATUS:    implemented
WHAT:      New config `configs/strategy_config.shadow_blend.json` — the last
           piece of the shadow_blend lane. Consumed by umbrella daily_104
           Step 5 (RenQuant#535, MERGED: the gate auto-activates the moment
           this profile appears in the pinned strategy configs, env tag
           `alpaca_shadow_blend`) and executed by the pipeline#218 composite
           `kind="blend"` scorer (certified z(prod)+z(clf),
           renquant-model#74/75/76 confirmatory line). Plus: allowlist entry
           + a pinned semantic test in `tests/test_strategy_configs.py`
           (`test_shadow_blend_profile_semantic_pins`).
WHY/DIR:   The lane runs the certified blend objective as PRIMARY scorer
           through the FULL decision funnel (candidates → veto → QP →
           sized intents), shadow-only (readonly broker, no submission),
           so the blend accrues live decision evidence like the PatchTST
           shadow does. Profile = strategy_config.json + EXACTLY five
           deltas (everything else pinned semantically identical by the
           new test):

           1. `ranking.panel_scoring.kind="blend"` + `components`
              (order-significant, pipeline#218 fail-closed pin semantics;
              both pins REQUIRED per component):
              - [0] prod scorer `artifacts/prod/panel-ltr.alpha158_fund.json`
                content `sha256:04d7a381cd6df847` (abbrev-16, the
                shadow_models convention), fp `sha256:f8fb2259b2bf1537`
                (verbatim — the artifact's stored form);
              - [1] clf `artifacts/shadow/panel-clf.top-decile.fwd60.json`
                content `sha256:6101a9fe5b200900` (TODAY'S model#83/
                strategy#67 re-stamp — the stale `99687a90` pin would
                fail-close), fp `sha256:1d8f167f…e41b` (verbatim, full).
              Top-level `artifact_path` KEPT = component 0's path: the
              strategy-repo loader (`config._validate_strategy_config`)
              requires it, and it anchors the preflight + strict
              config-consistency gates on the same prod artifact they
              check today (per #218 LoadScorerTask semantics; the
              BlendHandler ignores it for loading).
           2. `global_calibration.enabled=false` — THE OLD TRAP
              (shadow-config-FP-restamp): the prod calibrator binds the
              prod scorer fp via `strict_scorer_match`; against the blend
              composite fp (`sha256:a2a061a0cb3fe652…`) it would
              `config_mismatch` fail-close the whole lane. No calibrator
              stamped for the composite exists, so DISABLE is the only
              honest option (re-pointing was investigated: nothing
              compatible exists). Blend scores are already
              cross-sectionally normalized z-sums; admission uses the
              scale-free `adaptive_mean_std` buy floor on the raw blend
              score (rank_score = raw panel_score when calibration is
              off).
           3. `conviction_gate.enabled=false` — the gate floors on
              calibrator `expected_return`, which is set ONLY by
              ApplyGlobalCalibrationTask; with calibration off every
              candidate would drop as `conviction:mu_nan` (verified in
              job_panel_scoring.py:3061 + ConvictionGateTask).
           4. `ranking.kelly_sizing.enabled=false` —
              `use_calibrator_mu=true` wires Kelly μ from the calibrator;
              with it off ApplyKellySizingTask zeroes every target
              (`kelly_zero:mu_none`) and SizeAndEmit sizes 0 → no
              intents. Disabled ⇒ legacy regime max_position_pct ×
              conviction × σ multiplicative sizing sizes the shadow
              intents (verified in smoke: 3 sized BUY intents).
           5. `shadow_models`/`shadow_experiment` removed — this lane IS
              the blend; the clf + patchtst shadow legs stay on the
              prod/Step-4 lanes (no double-loading, no duplicate health
              records).

           QP μ CONTRACT (strict, kept): `rotation.joint_actions.
           qp_mu_contract="strict"` stays; `ranking.alpha_to_mu.enabled=
           true` (Grinold-Kahn) is the legal μ source per
           `_qp_mu_contract_reason` ("calibrator expected_return, NGBoost
           μ, or alpha_to_mu"). NOTE: the QP solver job is
           config-disabled in production (`rotation.joint_actions.
           enabled=false`) and this profile keeps prod parity, so
           `ValidateQPMuContractTask` does not execute in the daily
           funnel today — the contract keys are kept legal so a future
           QP re-enable cannot be poisoned by this profile. The
           signal-direction contract stays fully armed (smoke: MCHP
           BLOCKED `nonpositive_expected_return_no_long` on its
           per-ticker ER while its blend z was top-decile — the ER
           conjunct still bites when a per-ticker μ exists; it is a
           documented no-op only when no ER is present).

EVIDENCE:  [VERIFIED] Acceptance smoke = the ACTUAL Step-5 command
           (`renquant_orchestrator live-bridge --strategy renquant_104
           --broker readonly-alpaca --once --strategy-config-name
           strategy_config.shadow_blend.json` under
           `RENQUANT_READONLY_TAG=alpaca_shadow_blend`) + `--preflight`
           (the GOAL-5 AC5 dry-run probe: full funnel to the decision
           line, guaranteed no persistence/orders/ntfy), in an isolated
           umbrella worktree of RenQuant origin/main (post-#535) with
           `RENQUANT_SUBREPO_ROOT` runtime = pipeline @ #218 branch +
           this branch; state root inside the worktree; data root +
           per-ticker `models/` read from the live tree (the committed
           models/ snapshot is the stale April baseline — without the
           live models the universe collapses to 0, exactly the
           known trap; READ-only, dry-run guard attested no writes).
           Key lines (full set in the PR body):
           - `load_blend_scorer: component[0] … verified
             (content=sha256:04d7a381cd6df847… fp=sha256:f8fb2259b2bf1537)`
             + `component[1] … verified (content=sha256:6101a9fe5b200900…
             fp=sha256:1d8f167f…e41b)`
           - `LoadScorerTask: loaded blend artifact (features=172)`;
             `ApplyScoresTask[blend]: passing RAW union matrix (172
             features)`; `panel scored 84/84 candidates, 4/4 holdings`
           - `VetoWeakBuysTask: dropped 73 candidate(s) below rank_score
             floor=max(min=0.20, mean+1.00*std=1.681)` — the adaptive
             floor working scale-free on the blend z-sums
           - `SizeAndEmitTask: TSLA NEW_BUY 1 @ 309.22 (2.9% target)` /
             `ATI NEW_BUY 3 @ 192.64 (5.4%)` / `NEM NEW_BUY 6 @ 93.47
             (5.3%)`; `3 orders placed (spent=$1448)` — sized intents
             from the legacy multiplicative stack (Kelly off by design)
           - `funnel integrity: verdict=ECONOMIC_TRADE fired=0
             structural=False candidates_final=11 buys=3`
           - `[READONLY][ALPACA_SHADOW_BLEND]RENQUANT-104 [FULL
             (PREFLIGHT)] PREFLIGHT-DECISION reached`; attestation
             `{"persisted": false, "notified": false, "promoted": false,
             "ordered": false, "reached_decision": true}` — tag
             isolation (`live_state.alpaca_shadow_blend.json` in
             P-STATE-FILE) + zero side effects
           - preflight: 22/22 ✓ incl. `P-CALIBRATOR-HEALTH …
             global_calibration disabled; not applicable` and
             `P-MODEL-STALENESS kind='blend' unrecognized — staleness
             skip` (the #218-documented soft-skip)
           QP-contract note: the QP solver job itself is config-disabled
           in production (`rotation.joint_actions.enabled=false`,
           `_solver_note_20260609`) and stays so here (prod parity); the
           strict contract + alpha_to_mu remain configured so the lane
           stays legal if/when the QP path is re-enabled. The composite
           fp of the two pinned legs recomputes to
           `sha256:a2a061a0cb3fe652284af757fbd736b2c8d7a909ad016ad3a1f42f6186c23c70`
           (matches pipeline#218's smoke).
           Repo tests: 83 passed / 1 skipped (baseline 82/1; +1 = the
           new pinned semantic test).
NEXT:      Merge order: pipeline#218 FIRST (the kind must exist in the
           pinned pipeline), RenQuant#535 (MERGED 2026-07-27), then this
           profile; the pin advances that deploy the lane on the run
           machine are the coordinator's (pin sync — merged ≠ live).
           After the first real Step-5 run, eyeball
           `live_state.alpaca_shadow_blend.json` + the
           `[READONLY][ALPACA_SHADOW_BLEND]` ntfy for lane isolation.
