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
        "strategy_config.shadow_a.json",
        "strategy_config.shadow_b.json",
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


def test_execution_contract_is_explicit() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")

    assert cfg["execution"]["enabled"] is True
    assert cfg["execution"]["t2_settlement_days"] == 1
    assert cfg["execution"]["buying_power_mode"] == "non_marginable_buying_power"


def test_fractional_shares_contract_is_explicit_and_default_off() -> None:
    """S-FRAC v2 stage-2 config companion (renquant-pipeline #153; cash-drag
    phase-1 order in doc/design/2026-07-07-104-105-cash-drag-resolution.md).

    The block exists so fractional-sizing policy is declared in strategy
    config rather than living only in pipeline defaults, but it stays inert
    until the active-path capability gate, broker guard, and sizing-fidelity
    evidence are all proven. While disabled, 104 remains on the safe
    whole-share + A-3 fallback path."""
    for name in (
        "strategy_config.json",
        "strategy_config.golden.json",
        "strategy_config.shadow.json",
    ):
        cfg = load_strategy_config(CONFIG_DIR / name)
        frac = cfg["execution"]["fractional_shares"]
        assert frac["enabled"] is False, f"{name}: fractional sizing must stay default-OFF"
        assert frac["min_notional"] == 1.0
        assert frac["min_fractional_trade_notional"] == 25.0
        assert frac["non_fractionable_tickers"] == []
        assert "#153" in frac["_comment"], f"{name}: must cite renquant-pipeline #153"
        assert "sizing-fidelity evidence" in frac["_comment"], (
            f"{name}: enablement bar must be explained"
        )
        assert "2026-07-07 cash-drag phase-1" in frac["_provenance"]
        assert set(frac) == {
            "enabled",
            "min_notional",
            "min_fractional_trade_notional",
            "non_fractionable_tickers",
            "_comment",
            "_provenance",
        }, f"{name}: unexpected fractional_shares keys"


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
        # 2026-07-10: SHADOW logging enabled in prod+golden (JSONL only — no
        # orders, no capital movement; collects the RS-1 SS7 corpus that any
        # future mode=live decision is gated on). shadow.json (arm S-0.5,
        # single-delta contract) stays inert. mode=live remains gated on the
        # RS-1 §4 replay comparison + recorded capital authorization.
        expected_sleeve = name != "strategy_config.shadow.json"
        assert sleeve["enabled"] is expected_sleeve, (
            f"{name}: sleeve shadow-logging contract 2026-07-10"
        )
        assert sleeve["mode"] == "shadow", f"{name}: only shadow mode may be enabled"
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


# D6-§2a two-arm shadow A/B — the BINDING contract for the arm configs.
# doc/design/2026-07-09-governor-prereg-replay-protocol.md §2a on
# renquant-orchestrator main; the commit below is #443's merge commit.
SHADOW_AB_PROTOCOL_DOC = "doc/design/2026-07-09-governor-prereg-replay-protocol.md"
SHADOW_AB_PROTOCOL_COMMIT = "8981edfa2a2ef71f538bac5b965bc389f21a9eb7"
SHADOW_AB_TREATMENT_KEY = "ranking.panel_scoring.buy_floor_std_mult"
SHADOW_AB_ARM_ANNOTATION_KEY = "ranking.panel_scoring._arm"


def _diff_paths(a, b, prefix: str = "") -> set[str]:
    """Dotted paths at which two parsed JSON trees differ (missing keys count)."""
    if isinstance(a, dict) and isinstance(b, dict):
        paths: set[str] = set()
        for key in set(a) | set(b):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in a or key not in b:
                paths.add(child)
            else:
                paths |= _diff_paths(a[key], b[key], child)
        return paths
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        paths = set()
        for i, (va, vb) in enumerate(zip(a, b)):
            paths |= _diff_paths(va, vb, f"{prefix}[{i}]")
        return paths
    if type(a) is type(b) and a == b:
        return set()
    # bool is an int subclass; JSON 1 vs 1.0 vs true must not silently equate.
    if isinstance(a, bool) != isinstance(b, bool):
        return {prefix}
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a == b:
        return set()
    return {prefix} if a != b else set()


def test_shadow_ab_arm_configs_carry_frozen_2a_values() -> None:
    """D6-§2a two-arm shadow A/B — frozen NORMATIVE arm values (orchestrator
    #443 merged; §2a, 'Corrected design — two simultaneous isolated shadow
    arms, identical except the floor').

    Arm S-0.5 (TREATMENT)  = strategy_config.shadow_a.json, tag alpaca_shadow_a
    Arm S-1.0 (CONTROL)    = strategy_config.shadow_b.json, tag alpaca_shadow_b

    Both arms live in DEDICATED files, never the legacy strategy_config.
    shadow.json (Step-4 ops shadow, broker tag alpaca_shadow) — a Codex
    review on #53 caught an earlier draft mutating shadow.json in place,
    which would have silently re-armed the legacy single-arm shadow with
    the treatment before P-2 isolates the two new arms. See
    test_legacy_shadow_config_untouched_by_shadow_ab below.

    Both arms: scorer hf_patchtst, Kelly fractional 0.5 / max_concentration
    0.35, BULL_CALM max_position_pct 0.15, one_share_floor_enabled true,
    buy_floor adaptive_mean_std. The ONE functional delta is
    buy_floor_std_mult: 0.5 (treatment) vs 1 (control, production's floor
    multiple). The broker-state tags are threaded by the P-2 orchestrator
    two-arm runner (orchestrator #451), NOT by config keys — the r5 draft's
    second config key (live.preflight.strict shim) is WITHDRAWN in §2a, so
    NO 'live' section may appear in either arm. Rewrite these pins ONLY under
    a new protocol version: §2a's treatment-fingerprint drift rule VOIDS the
    running experiment if either arm's resolved config hash changes mid-run."""
    arm_a = load_strategy_config(CONFIG_DIR / "strategy_config.shadow_a.json")
    arm_b = load_strategy_config(CONFIG_DIR / "strategy_config.shadow_b.json")

    for name, cfg in (("shadow_a", arm_a), ("shadow_b", arm_b)):
        panel = cfg["ranking"]["panel_scoring"]
        assert panel["kind"] == "hf_patchtst", f"{name}: §2a frozen scorer"
        assert panel["buy_floor"] == "adaptive_mean_std", (
            f"{name}: §2a freezes buy_floor=adaptive_mean_std in BOTH arms"
        )
        assert cfg["ranking"]["kelly_sizing"]["fractional"] == 0.5, name
        assert cfg["ranking"]["kelly_sizing"]["max_concentration"] == 0.35, name
        assert cfg["regime_params"]["BULL_CALM"]["max_position_pct"] == 0.15, name
        assert cfg["sizing"]["one_share_floor_enabled"] is True, name
        # Withdrawn r5 preflight shim must NOT come back as a config key:
        # arm-symmetric preflight policy is P-2-owned (§2a execution plan).
        assert "live" not in cfg, (
            f"{name}: the live.preflight.strict shim is WITHDRAWN by §2a"
        )
        # Provenance: the arm files must cite the merged protocol + commit.
        reason = panel["_buy_floor_reason"]
        assert SHADOW_AB_PROTOCOL_DOC in reason, name
        assert SHADOW_AB_PROTOCOL_COMMIT in reason, name

    assert arm_a["ranking"]["panel_scoring"]["buy_floor_std_mult"] == 0.5
    assert arm_b["ranking"]["panel_scoring"]["buy_floor_std_mult"] == 1

    # Arm identity annotations carry the frozen §2a broker-state tags
    # (runner-threaded; deliberately NOT functional config keys).
    arm_a_note = arm_a["ranking"]["panel_scoring"]["_arm"]
    arm_b_note = arm_b["ranking"]["panel_scoring"]["_arm"]
    assert "S-0.5 TREATMENT" in arm_a_note
    assert "alpaca_shadow_a" in arm_a_note
    assert "S-1.0 CONTROL" in arm_b_note
    assert "alpaca_shadow_b" in arm_b_note


def test_shadow_ab_arms_differ_in_exactly_the_treatment_key() -> None:
    """§2a config-drift pin, enforced LITERALLY: shadow_b is 'a clone of
    shadow_a.json differing in exactly ONE functional key (plus inert
    `_reason` annotation strings)'. Three independent enforcements: (1)
    line-level — the two files have identical line counts and differ on
    exactly the buy_floor_std_mult line and the _arm annotation line; (2)
    tree-level — the parsed-JSON diff is exactly those two dotted paths;
    (3) byte-level — with those two paths removed, the canonical
    serializations are byte-equal."""
    a_text = (CONFIG_DIR / "strategy_config.shadow_a.json").read_text()
    b_text = (CONFIG_DIR / "strategy_config.shadow_b.json").read_text()

    # (1) line-level: same shape, exactly two differing lines, on known keys.
    a_lines = a_text.splitlines()
    b_lines = b_text.splitlines()
    assert len(a_lines) == len(b_lines), "arm files must be line-for-line clones"
    differing = [
        (la, lb) for la, lb in zip(a_lines, b_lines) if la != lb
    ]
    differing_keys = sorted(
        la.strip().split(":")[0].strip().strip('"') for la, _ in differing
    )
    assert differing_keys == ["_arm", "buy_floor_std_mult"], (
        f"arm files may differ ONLY on the treatment key and the _arm "
        f"annotation; got differing lines for {differing_keys}"
    )

    # (2) tree-level: the full recursive diff is exactly the two paths.
    arm_a = json.loads(a_text)
    arm_b = json.loads(b_text)
    assert _diff_paths(arm_a, arm_b) == {
        SHADOW_AB_TREATMENT_KEY,
        SHADOW_AB_ARM_ANNOTATION_KEY,
    }

    # (3) byte-level: everything else is byte-equal under canonical dump.
    for cfg in (arm_a, arm_b):
        panel = cfg["ranking"]["panel_scoring"]
        del panel["buy_floor_std_mult"]
        del panel["_arm"]
    assert json.dumps(arm_a, sort_keys=True) == json.dumps(arm_b, sort_keys=True)


def test_shadow_ab_leaves_prod_and_golden_at_production_baseline() -> None:
    """§2a prerequisite-PR contract: the config-only treatment PR verifies
    'prod/golden untouched'. Pin the production baseline on every §2a-relevant
    key so the shadow A/B cannot leak into the live book: the production
    buy-floor stays adaptive_mean_std at 1.0σ (XGB primary), sizing stays at
    the production Kelly 0.3/0.12, BULL_CALM 0.12, one-share floor OFF. Live
    enablement of the 0.5σ treatment is a SEPARATE future PR carrying the §2a
    Tier-2 verdict memo + pre-registration gate + Codex review (§2a decision
    rule) — never this pin silently drifting."""
    for name in ("strategy_config.json", "strategy_config.golden.json"):
        cfg = load_strategy_config(CONFIG_DIR / name)
        panel = cfg["ranking"]["panel_scoring"]
        assert panel["kind"] == "xgb", f"{name}: production primary stays XGB"
        assert panel["buy_floor"] == "adaptive_mean_std", name
        assert panel["buy_floor_std_mult"] == 1, (
            f"{name}: production floor multiple stays 1.0σ — flipping it is a "
            "live-book behavior change requiring the §2a verdict memo + "
            "pre-registration gate + Codex review in its own PR"
        )
        assert cfg["ranking"]["kelly_sizing"]["fractional"] == 0.3, name
        assert cfg["ranking"]["kelly_sizing"]["max_concentration"] == 0.12, name
        assert cfg["regime_params"]["BULL_CALM"]["max_position_pct"] == 0.12, name
        assert cfg["sizing"]["one_share_floor_enabled"] is False, name


def test_legacy_shadow_config_untouched_by_shadow_ab() -> None:
    """Codex review on #53: an earlier draft of this PR mutated
    strategy_config.shadow.json IN PLACE to the 0.5σ treatment values. That
    file is the LEGACY Step-4 ops shadow config (broker tag alpaca_shadow,
    still invoked daily by daily_104.sh independent of the D6-§2a
    experiment). Mutating it would have silently re-armed the legacy
    single-arm shadow with an uncontrolled treatment observation before
    P-2 isolates the two new arms (alpaca_shadow_a/_b) — contaminating the
    paired experiment. Pin the legacy file at its PRE-experiment values:
    adaptive_quantile / std_mult 1 (the 2026-06-11 false-BEAR audit
    values), with no _arm annotation and no reference to the D6-§2a
    protocol anywhere in it. The two-arm experiment lives ENTIRELY in
    strategy_config.shadow_a.json / strategy_config.shadow_b.json."""
    legacy = load_strategy_config(CONFIG_DIR / "strategy_config.shadow.json")
    panel = legacy["ranking"]["panel_scoring"]
    assert panel["buy_floor"] == "adaptive_quantile", (
        "legacy shadow.json must stay at its pre-#53 adaptive_quantile "
        "value — the D6-§2a treatment must never leak into the legacy "
        "Step-4 ops shadow path"
    )
    assert panel["buy_floor_std_mult"] == 1, (
        "legacy shadow.json must stay at its pre-#53 std_mult=1 value"
    )
    assert "_arm" not in panel, (
        "legacy shadow.json must carry no D6-§2a arm annotation — it is "
        "not part of the two-arm experiment"
    )
    reason = panel.get("_buy_floor_reason", "")
    assert SHADOW_AB_PROTOCOL_DOC not in reason, (
        "legacy shadow.json must not cite the §2a protocol — it is not "
        "one of the experiment's arms"
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
