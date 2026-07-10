from __future__ import annotations

import json
from pathlib import Path

import pytest

from renquant_strategy_104 import load_strategy_config, strategy_manifest


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"
LATEST_PRODUCTION_SYNC_SOURCE = "732704bdb00c5bda6a9f6a4ee4c33523c0824286"


def _load(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text())


def test_required_policy_configs_exist_and_parse() -> None:
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
        "xgb_prod_artifact_manifest.json",
    ):
        data = _load(name)
        assert isinstance(data, dict)
        if name.startswith("strategy_config"):
            assert data.get("watchlist"), f"{name} missing watchlist"
            assert data.get("regime_params"), f"{name} missing regime_params"


def test_active_and_golden_watchlist_match() -> None:
    active = _load("strategy_config.json")
    golden = _load("strategy_config.golden.json")
    assert active["watchlist"] == golden["watchlist"]


def test_active_and_golden_semantic_config_match() -> None:
    active = _load("strategy_config.json")
    golden = _load("strategy_config.golden.json")

    active_norm = _strip_provenance(active)
    golden_norm = _strip_provenance(golden)
    # Production active currently carries the selected WF manifest; golden
    # remains the policy baseline. Keep that explicit rather than blocking the
    # production sync.
    active_wf = active_norm.pop("walkforward", None)
    golden_wf = golden_norm.pop("walkforward", None)
    assert active_wf == {
        "manifest_path": (
            "/Users/renhao/git/github/RenQuant/backtesting/renquant_104/"
            "artifacts/sim/walkforward_manifest_dropsenti_v3.json"
        )
    }
    assert golden_wf is None
    assert active_norm == golden_norm


def test_cash_drag_slot_counts_stay_at_production_8_3() -> None:
    """Pin the production slot counts so the 2026-06-29 cash-drag analysis
    (PR #35) stays PROPOSAL-ONLY and cannot silently raise live policy.

    A real 2026-06-29 daily-full deployed only $827 of $8,730 buying power
    (live book ~46% deployed) because two slot caps -- top-level
    max_concurrent_positions and rotation.panel_buy_top_n -- bounded how many
    small positions the book can hold. A readonly 8/3 vs 10/4 replay run today
    on the live book showed the slot-raise is a WEAK fix: 10/4 deploys only
    ~$427 more (CVX + ZM) while the genuinely better high-price names
    (AVGO/BLK/GS) were selected but skipped by whole-share rounding because
    their Kelly targets (~$400, ~4%) are smaller than one share. The real lever
    is FRACTIONAL SHARES, not slot count, so active/golden stay at the
    production 8/3 and this PR merges as the analysis record only. See
    doc/design/2026-06-29-cash-drag-raise-slots.md. Active and golden must
    agree for the CI semantic-match contract."""
    active = _load("strategy_config.json")
    golden = _load("strategy_config.golden.json")

    assert active["max_concurrent_positions"] == 8
    assert golden["max_concurrent_positions"] == 8
    assert active["rotation"]["panel_buy_top_n"] == 3
    assert golden["rotation"]["panel_buy_top_n"] == 3
    assert (
        active["max_concurrent_positions"]
        == golden["max_concurrent_positions"]
    )
    assert (
        active["rotation"]["panel_buy_top_n"]
        == golden["rotation"]["panel_buy_top_n"]
    )

    # Per-name and per-sector risk and Kelly aggression are deliberately NOT
    # touched -- guard against an accidental risk relaxation.
    assert active["ranking"]["kelly_sizing"]["fractional"] == 0.3
    assert active["ranking"]["kelly_sizing"]["max_concentration"] == 0.12
    assert active["regime_params"]["BULL_CALM"]["max_position_pct"] == 0.12
    assert active["max_positions_per_sector"] == 6


def test_conviction_gate_demean_is_off_and_mu_floor_pinned() -> None:
    """Pin the conviction-gate intent so it cannot silently drift (PR #34 /
    2026-06-29 emergency revert). demean_cross_sectional MUST be false in both
    active and golden — with demean ON the absolute mu_floor=0.03 is applied to a
    relative (demeaned) quantity, which on the fresh fundamentals feed admitted
    ZERO names (run 2026-06-29-live-5970796e: max mu 0.0505, xs_mean +0.0212, so
    even the top name demeaned to 0.0293 < 0.03). mu_floor stays 0.03 on raw mu."""
    for name in ("strategy_config.json", "strategy_config.golden.json"):
        cfg = load_strategy_config(CONFIG_DIR / name)
        gate = cfg["ranking"]["panel_scoring"]["conviction_gate"]
        assert gate["enabled"] is True
        assert gate["demean_cross_sectional"] is False, (
            f"{name}: demean_cross_sectional must be false (emergency revert PR #34)"
        )
        assert gate["mu_floor"] == 0.03, f"{name}: mu_floor must stay 0.03"


def test_sector_map_covers_active_watchlist() -> None:
    cfg = _load("strategy_config.json")
    sector_map = cfg.get("sector_map", {})
    missing = sorted(t for t in cfg["watchlist"] if t not in sector_map)
    assert missing == []


def test_watchlist_is_unique_and_contains_benchmark() -> None:
    cfg = _load("strategy_config.json")

    assert len(cfg["watchlist"]) == len(set(cfg["watchlist"]))
    assert cfg["benchmark"] in cfg["watchlist"]


def test_bull_calm_new_buys_and_panel_scorer_contract_are_explicit() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")
    panel = cfg["ranking"]["panel_scoring"]
    global_cal = panel["global_calibration"]

    assert cfg["regime_params"]["BULL_CALM"]["disable_new_buys"] is False
    assert panel["enabled"] is True
    assert panel["kind"] == "xgb"
    assert panel["artifact_path"] == "artifacts/prod/panel-ltr.alpha158_fund.json"
    assert global_cal["enabled"] is True
    assert global_cal["strict_scorer_match"] is True
    assert global_cal["artifact_path"] == "artifacts/prod/panel-rank-calibration.json"
    # Conviction gate (renquant-pipeline #140) is the quality guard that makes the
    # XGB primary deployable: only buy calibrated E[R-SPY] >= 3%.
    assert panel["conviction_gate"]["enabled"] is True
    assert panel["conviction_gate"]["mu_floor"] == 0.03
    assert panel["regime_admission"]["enabled"] is False
    # PatchTST is now the readonly shadow.
    assert shadow["ranking"]["panel_scoring"]["kind"] == "hf_patchtst"
    assert "patchtst_shadow" in shadow["ranking"]["panel_scoring"]["artifact_path"]


def test_xgb_operator_promotion_contract_is_auditable() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    golden = load_strategy_config(CONFIG_DIR / "strategy_config.golden.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")
    panel = cfg["ranking"]["panel_scoring"]
    golden_panel = golden["ranking"]["panel_scoring"]
    shadow_panel = shadow["ranking"]["panel_scoring"]

    promotion_note = panel.get("_2026_06_23_xgb_promotion", "")
    assert "operator-directed prod/shadow switch" in promotion_note
    assert "XGB" in promotion_note
    assert "PatchTST moved to readonly shadow" in promotion_note

    assert panel["kind"] == golden_panel["kind"] == "xgb"
    assert panel["artifact_path"] == golden_panel["artifact_path"]
    assert panel["artifact_path"] == "artifacts/prod/panel-ltr.alpha158_fund.json"
    assert panel["global_calibration"] == golden_panel["global_calibration"]
    assert panel["global_calibration"]["strict_scorer_match"] is True
    assert (
        panel["global_calibration"]["artifact_path"]
        == "artifacts/prod/panel-rank-calibration.json"
    )
    assert panel["conviction_gate"]["mu_floor"] == 0.03
    assert panel["regime_admission"]["enabled"] is False
    assert (
        "XGB trades ALL regimes"
        in panel["regime_admission"]["_promotion_reason_2026_06_23"]
    )

    shadow_models = panel.get("shadow_models") or []
    assert shadow_models == [
        {
            "name": "hf_patchtst_pt07_strict_seed44_previous_primary",
            "kind": "hf_patchtst",
            "artifact_path": shadow_panel["artifact_path"],
            "_2026_06_23_role": (
                "Previous primary scorer moved to strategy_config.shadow.json "
                "after XGB promotion."
            ),
        }
    ]
    assert (
        panel["shadow_experiment"]
        == "renquant_104_patchtst_shadow_after_xgb_promotion"
    )
    assert shadow_panel["kind"] == "hf_patchtst"
    assert "patchtst_shadow" in shadow_panel["artifact_path"]
    assert "production primary is XGB" in shadow["ranking"].get(
        "_2026_06_23_shadow_switch", ""
    )


def test_xgb_prod_artifact_manifest_matches_runtime_configs() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    golden = load_strategy_config(CONFIG_DIR / "strategy_config.golden.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")
    manifest = _load("xgb_prod_artifact_manifest.json")
    panel = cfg["ranking"]["panel_scoring"]
    golden_panel = golden["ranking"]["panel_scoring"]
    shadow_panel = shadow["ranking"]["panel_scoring"]
    primary = manifest["production_primary"]
    primary_cal = primary["global_calibration"]
    shadow_manifest = manifest["readonly_shadow"]

    assert manifest["schema_version"] == 1
    assert manifest["strategy"] == "renquant_104"
    assert manifest["manifest_role"] == "operator_override_directive_audit"
    assert manifest["promotion_boundary"]["decision"] == (
        "operator_directed_prod_shadow_switch"
    )
    assert manifest["promotion_boundary"]["primary_model_family"] == "xgb"
    assert manifest["promotion_boundary"]["acceptance_status"] == (
        "operator_override_with_residual_controls"
    )

    # Scope is narrowed to an exceptional, withdrawable override — NOT a promotion.
    scope = manifest["scope_claim"]
    assert "operator directive" in scope["this_is"]
    assert "normal production promotion" in scope["this_is_not"]
    assert scope["positive_claims_only"] and scope["explicitly_not_claimed"]
    assert any("does not" in c.lower() for c in scope["explicitly_not_claimed"])

    assert primary["kind"] == panel["kind"] == golden_panel["kind"] == "xgb"
    assert primary["artifact_path"] == panel["artifact_path"] == golden_panel["artifact_path"]
    assert primary["artifact_path_role"] == "production_primary"

    runtime_cal = panel["global_calibration"]
    assert primary_cal["enabled"] == runtime_cal["enabled"] is True
    assert primary_cal["strict_scorer_match"] == runtime_cal["strict_scorer_match"] is True
    assert primary_cal["artifact_path"] == runtime_cal["artifact_path"]
    assert primary_cal["artifact_path"] == golden_panel["global_calibration"]["artifact_path"]
    assert primary_cal["artifact_path_role"] == "production_primary_calibrator"

    assert primary["conviction_gate"]["mu_floor"] == panel["conviction_gate"]["mu_floor"] == 0.03
    assert primary["regime_admission"]["enabled"] == panel["regime_admission"]["enabled"] is False

    assert shadow_manifest["name"] == "hf_patchtst_pt07_strict_seed44_previous_primary"
    assert shadow_manifest["kind"] == shadow_panel["kind"] == "hf_patchtst"
    assert shadow_manifest["artifact_path"] == shadow_panel["artifact_path"]
    assert shadow_manifest["config_path"] == "configs/strategy_config.shadow.json"
    assert shadow_manifest["experiment"] == panel["shadow_experiment"]

    # The override is honestly recorded: XGB did not pass the gate; risks disclosed.
    assert "conviction_gate mu_floor 0.03" in manifest["residual_controls"]
    assert "calibrator strict_scorer_match" in manifest["residual_controls"]
    assert any("FAILED the WF promotion gate" in r for r in manifest["disclosed_risks"])
    assert any("Lags SPY" in r for r in manifest["disclosed_risks"])
    assert any(
        "Strengthen the BULL_CALM" in c for c in manifest["follow_up_exit_criteria"]
    )
    # Path B evidence: threshold sensitivity + honest caveat + concrete withdrawal trigger.
    assert "mu_floor_evidence" in manifest
    assert "coarse quality filter" in manifest["mu_floor_evidence"]["honest_caveat"].lower() \
        or "COARSE QUALITY FILTER" in manifest["mu_floor_evidence"]["honest_caveat"]
    assert manifest["mu_floor_evidence"]["threshold_sensitivity_top_of_cross_section"]["mu_by_name"]["CRWD"] == 0.053
    assert any("regime_admission" in t for t in manifest["override_withdrawal_trigger"])


def test_admission_breadth_shadow_ab_treatment_and_prod_baseline_pinned() -> None:
    """Preregistered admission-breadth shadow A/B
    (doc/design/2026-07-10-admission-breadth-shadow-ab.md; orchestrator #443
    D6 protocol §2 Phase-2 amendment — veto arms moved to live shadow because
    replay bars lack pre-veto candidates; successor to CLOSED #47 with its
    review blockers fixed).

    BASELINE arm: production AND golden stay at adaptive_mean_std with
    buy_floor_std_mult == 1.0. Flipping production to 0.5 is the LIVE
    ENABLEMENT act — a live-book behavior change requiring >= 10 future-only
    shadow sessions, the marginal-entrant quality bar, a recommendation memo,
    and its own codex-reviewed PR (design doc §9). Rewrite this pin ONLY
    alongside that recorded decision (house pattern: intraday mode pin,
    fingerprint pin, sleeve pin).

    TREATMENT arm: the shadow config carries adaptive_mean_std with
    buy_floor_std_mult == 0.5. Both keys moved together deliberately: under
    the superseded adaptive_quantile mode the std-mult was dead config, and a
    dead-config flip would be a deployed-but-dark non-experiment. Shadow runs
    the full funnel on isolated alpaca_shadow state; zero live orders."""
    prod = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    golden = load_strategy_config(CONFIG_DIR / "strategy_config.golden.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")

    for name, cfg in (("strategy_config.json", prod), ("strategy_config.golden.json", golden)):
        panel = cfg["ranking"]["panel_scoring"]
        assert panel["buy_floor"] == "adaptive_mean_std", name
        assert panel["buy_floor_std_mult"] == 1, (
            f"{name}: production/golden buy_floor_std_mult must stay 1.0 — "
            "0.5 in production is the live enablement decision (separate "
            "gated PR after the shadow A/B verdict memo, design doc §9)"
        )

    shadow_panel = shadow["ranking"]["panel_scoring"]
    assert shadow_panel["buy_floor"] == "adaptive_mean_std"
    assert shadow_panel["buy_floor_std_mult"] == 0.5
    reason = shadow_panel["_buy_floor_reason"]
    assert "2026-07-10-admission-breadth-shadow-ab" in reason
    assert "alpaca_shadow" in reason
    assert "NOT a calibrated optimum" in reason


def test_execution_contract_is_explicit() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")

    assert cfg["execution"]["enabled"] is True
    assert cfg["execution"]["t2_settlement_days"] == 1
    assert cfg["execution"]["buying_power_mode"] == "non_marginable_buying_power"


def test_qp_cap_compliance_sells_are_enabled_without_relaxing_c2() -> None:
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        qp = cfg["rotation"]["joint_actions"]
        assert qp["qp_c2_infeasible_policy"] == "strict"
        assert qp["allow_cap_compliance_sells_on_infeasible"] is True
        assert "never admits new buys" in qp["_allow_cap_compliance_sells_on_infeasible_reason"]


def test_qp_live_shadow_telemetry_is_enabled_readonly() -> None:
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        telemetry = cfg["rotation"]["joint_actions"]["qp_live_shadow_telemetry"]
        assert telemetry["enabled"] is True
        assert telemetry["candidate_name"] == "hybrid_option_f_allocator"
        assert telemetry["incumbent_name"] == "current_qp"
        assert telemetry["path"] == "artifacts/live-shadow/qp-live-shadow.jsonl"
        assert "readonly JSONL telemetry only" in telemetry["_reason"]


def test_kelly_sigma_horizon_matches_mu_horizon() -> None:
    """2026-06-11 Kelly horizon-match fix: f*=mu/sigma^2 requires mu and sigma
    on the SAME horizon. mu is the 60d calibrator expected return, so
    sigma_horizon_days must be 60 (was 252/annualized, which inflated variance
    ~4.2x and systematically crushed high-vol names). Prod + golden now carry
    the matched 60d horizon; this replaces the prior 'shadow-only experiment'
    guard that pinned prod to 252 for byte-equivalence."""
    prod = load_strategy_config(CONFIG_DIR / "strategy_config.json")
    golden = load_strategy_config(CONFIG_DIR / "strategy_config.golden.json")
    shadow = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")

    assert prod["ranking"]["kelly_sizing"]["sigma_horizon_days"] == 60
    assert golden["ranking"]["kelly_sizing"]["sigma_horizon_days"] == 60
    # half-Kelly retuned down to 0.3 so the (now correctly larger) targets keep
    # total deployment sane rather than pinning every name at the 12% cap.
    assert prod["ranking"]["kelly_sizing"]["fractional"] == 0.3
    assert golden["ranking"]["kelly_sizing"]["fractional"] == 0.3
    # shadow already ran the matched 60d horizon.
    assert shadow["ranking"]["kelly_sizing"]["sigma_horizon_days"] == 60


def test_soft_exit_min_holding_days_cover_unlisted_regimes() -> None:
    """The sell-side BL-4 follow-up: panel/QP soft-exit horizon guards must
    keep a 60d default in regimes not explicitly listed."""
    for name in ("strategy_config.json", "strategy_config.golden.json"):
        cfg = load_strategy_config(CONFIG_DIR / name)
        panel_days = cfg["risk"]["panel_exit"]["min_holding_days_by_regime"]
        qp_days = cfg["rotation"]["joint_actions"]["qp_soft_sell_guard"][
            "min_holding_days_by_regime"
        ]

        assert panel_days["BULL_CALM"] == 60
        assert panel_days["default"] == 60
        assert qp_days["BULL_CALM"] == 60
        assert qp_days["default"] == 60


def test_core_regime_max_hold_is_far_backstop_in_all_runtime_configs() -> None:
    """Max-hold is a zombie-position backstop, not a per-regime thesis clock."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        values = {
            regime: cfg["regime_params"][regime]["max_hold_days"]
            for regime in ("BULL_CALM", "BULL_VOLATILE", "CHOPPY", "BEAR")
        }
        assert values == {
            "BULL_CALM": 500,
            "BULL_VOLATILE": 500,
            "CHOPPY": 500,
            "BEAR": 500,
        }


def test_bear_defensive_sleeve_is_explicit_and_default_off() -> None:
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        sleeve = cfg["bear_defensive_sleeve"]
        assert sleeve["enabled"] is False
        assert "A/B validation" in sleeve["_reason"]
        assert cfg["bear_defensive_slots"] > 0
        assert cfg["bear_defensive_pct"] > 0
        assert cfg["defensive_tickers"]


def test_parking_sleeve_keys_are_explicit_inert_and_shadow_only() -> None:
    """S7 parking-sleeve config companion (renquant-pipeline #157, RS-1 memo):
    the keys exist so the sleeve contract is declared in policy rather than
    living only in the pipeline's safe defaults, but the sleeve stays INERT
    (enabled=false) and SHADOW-only until the RS-1 §4 replay comparison and a
    separately recorded capital authorization. The values below mirror the
    pipeline defaults exactly, so defining them changes nothing. SGOV is
    deliberately NOT a watchlist entry: sleeve-leg price coverage is an
    umbrella follow-up (the daily price fetch is umbrella-owned, and #157's
    shadow tolerates SGOV absence), and the alpha universe / cross-sectional
    admission stats must never include a T-bill ETF."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        sleeve = cfg["sleeve"]
        assert sleeve["enabled"] is False, f"{name}: parking sleeve must stay inert"
        assert sleeve["mode"] == "shadow", f"{name}: only shadow mode is implemented"
        assert sleeve["spy_symbol"] == "SPY"
        assert sleeve["sgov_symbol"] == "SGOV"
        assert sleeve["reserve_pv_pct"] == 0.05
        assert sleeve["beta_max"] == 0.6
        assert sleeve["beta_pos"] == 1.0
        assert sleeve["min_trade_notional"] == 50.0
        assert sleeve["dd_budget_pct"] == 0.15
        assert sleeve["log_path"] == "logs/parking_sleeve_shadow.jsonl"
        assert "RS-1" in sleeve["_comment"], f"{name}: sleeve must cite RS-1 lineage"
        # SPY leg is already priced via the watchlist; SGOV coverage is the
        # umbrella follow-up, NOT an alpha-universe entry.
        assert sleeve["spy_symbol"] in cfg["watchlist"]
        assert sleeve["sgov_symbol"] not in cfg["watchlist"]


def test_intraday_decisioning_keys_match_scheduler_defaults_and_stay_shadow_only() -> None:
    """renquant105 Stage-1 SHADOW arming (RFC #208 §8.3/§10; consumer:
    renquant-orchestrator #266 ``intraday_session_scheduler.load_intraday_config``;
    #266 landing-checklist step 3, config half).

    Every value below mirrors the scheduler's safe defaults exactly, so
    defining the keys changes no scheduler behavior — the section's one real
    bit is ``enabled=true``, which is ONE of three independent gates: the
    scheduler is a SEPARATE launchd-run process (nothing in the daily run
    invokes it) and also requires the env kill switch
    ``RENQUANT_INTRADAY_DECISIONING`` truthy AND the kill-switch file absent,
    both machine-side ask-first landing steps. Until that install, this
    config is inert.

    THE STAGE-2 BAR, MECHANICALLY: ``mode`` must be ``"shadow"``. #266
    runtime-asserts never-submit on every tick and structurally downgrades
    ``mode="live"`` to shadow (§9.3a) — but authorizing live is a policy
    decision that must be VISIBLE, so this pin makes any flip to "live" fail
    the suite until the Stage-2 authorization deliberately rewrites this
    test alongside the config."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        intraday = cfg["intraday_decisioning"]
        # The one real bit: config gate armed (inert without the machine-side
        # env flag + launchd install; see the section _comment).
        assert intraday["enabled"] is True, f"{name}: Stage-1 shadow arming"
        # The Stage-2 authorization bar: shadow-only, pinned.
        assert intraday["mode"] == "shadow", (
            f"{name}: mode='live' is a Stage-2 authorization (RFC #208 §9.3a) "
            "— rewrite this pin ONLY alongside that recorded decision"
        )
        # Scheduler defaults (§5/§11b), mirrored exactly.
        assert intraday["tick_seconds"] == 720
        assert intraday["entry_open_delay_seconds"] == 300
        assert intraday["entry_close_cutoff_seconds"] == 1800
        assert intraday["canary_allowlist"] == []
        # null => the scheduler's default kill-switch path
        # (<data_root>/data/rq105/intraday_decisioning.KILL).
        assert intraday["kill_switch_file"] is None
        assert "#208" in intraday["_comment"], f"{name}: must cite RFC #208"
        assert "#266" in intraday["_comment"], f"{name}: must cite orchestrator #266"
        # No stray keys: the scheduler reads exactly this set (fail-closed on
        # malformed values); a typo'd extra key would silently do nothing.
        assert set(intraday) == {
            "enabled",
            "mode",
            "tick_seconds",
            "entry_open_delay_seconds",
            "entry_close_cutoff_seconds",
            "canary_allowlist",
            "kill_switch_file",
            "_comment",
        }, f"{name}: unexpected intraday_decisioning keys"


def test_fingerprint_accept_legacy_stamps_is_explicit_and_true() -> None:
    """M6 stage-2 step 1, config half (renquant-orchestrator
    ``doc/design/2026-07-03-m6-stage2-fingerprint-migration.md`` §3 step 1;
    reader: renquant-pipeline #164
    ``fingerprint_dispatch.accept_legacy_stamps``, absent => true).

    Explicit ``true`` equals the reader's default, so merging this changes
    NOTHING running today. The point is declaring the migration window
    (version-dispatched fingerprint verification accepts legacy versionless
    stamps alongside schema-v1 at both fail-closed checks:
    ``_assert_calibrator_matches_scorer`` and
    ``_assert_calibrator_matches_entry``) in POLICY, so the future flip is a
    reviewable strategy-config PR instead of a silent code-default change.

    THE STEP-4 BAR, MECHANICALLY: flipping to ``false`` (v1-only — a
    versionless stamp then fails closed with the re-stamp-under-v1 remedy) is
    the deliberate stage-2 STEP-4 migration act, gated on the step-3 census
    running green over the full observation window (design §3 steps 3-4).
    This pin makes any flip fail this repo's suite until the step-4 decision
    deliberately rewrites the test alongside the config — mirroring the
    intraday ``mode == "shadow"`` pin (PR #41) and the sleeve inertness pin
    (PR #39)."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        fingerprint = cfg["ranking"]["panel_scoring"]["fingerprint"]
        assert fingerprint["accept_legacy_stamps"] is True, (
            f"{name}: accept_legacy_stamps=false is the M6 stage-2 STEP-4 "
            "migration act (v1-only verification; design §3 step 4) — rewrite "
            "this pin ONLY alongside that recorded decision, after the step-3 "
            "census is green"
        )
        comment = fingerprint["_comment"]
        assert "#164" in comment, f"{name}: must cite pipeline #164 (the reader)"
        assert "2026-07-03-m6-stage2-fingerprint-migration" in comment, (
            f"{name}: must cite the M6 stage-2 design doc"
        )
        # Exactly the key #164's reader consumes (+ provenance): a typo'd
        # extra key under this section would silently do nothing.
        assert set(fingerprint) == {"accept_legacy_stamps", "_comment"}, (
            f"{name}: unexpected fingerprint keys"
        )


def test_strategy_repo_has_no_generated_experiment_configs() -> None:
    generated = sorted(
        p.name for p in CONFIG_DIR.glob("strategy_config.*.json")
        if ".sim_" in p.name or ".codex_" in p.name or ".whatif_" in p.name
    )
    assert generated == []


def test_strategy_package_loads_and_fingerprints_active_config() -> None:
    cfg_path = CONFIG_DIR / "strategy_config.json"
    cfg = load_strategy_config(cfg_path)
    manifest = strategy_manifest(cfg_path)

    assert cfg["watchlist"]
    assert manifest["strategy"] == "renquant_104"
    assert manifest["fingerprint"].startswith("sha256:")
    assert manifest["watchlist_size"] == len(cfg["watchlist"])


def test_readme_records_latest_production_sync_source() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert LATEST_PRODUCTION_SYNC_SOURCE in readme


def test_loader_rejects_duplicate_watchlist_and_missing_sector(tmp_path: Path) -> None:
    cfg = _load("strategy_config.json")
    cfg["watchlist"] = ["AAPL", "AAPL", "MSFT"]
    cfg["sector_map"] = {"AAPL": "Technology"}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate tickers"):
        load_strategy_config(path)


def test_loader_rejects_local_absolute_artifact_path(tmp_path: Path) -> None:
    cfg = _load("strategy_config.json")
    cfg["ranking"]["panel_scoring"]["artifact_path"] = "/Users/renhao/model.json"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ValueError, match="repo-relative"):
        load_strategy_config(path)


def _strip_provenance(value):
    if isinstance(value, dict):
        return {
            k: _strip_provenance(v)
            for k, v in value.items()
            if not str(k).startswith("_")
        }
    if isinstance(value, list):
        return [_strip_provenance(v) for v in value]
    return value
