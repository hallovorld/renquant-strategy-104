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
    assert manifest["manifest_role"] == "production_primary_scorer_audit"
    assert manifest["promotion_boundary"]["decision"] == (
        "operator_directed_prod_shadow_switch"
    )
    assert manifest["promotion_boundary"]["primary_model_family"] == "xgb"
    assert manifest["promotion_boundary"]["acceptance_status"] == (
        "operator_override_with_residual_controls"
    )

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
