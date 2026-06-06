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
    ):
        data = _load(name)
        assert isinstance(data, dict)
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
    assert panel["kind"] == "hf_patchtst"
    assert "patchtst_shadow" in panel["artifact_path"]
    assert global_cal["enabled"] is True
    assert global_cal["strict_scorer_match"] is True
    assert "panel-rank-calibration.hf_patchtst" in global_cal["artifact_path"]
    assert panel["regime_admission"]["enabled"] is False
    assert shadow["ranking"]["panel_scoring"]["kind"] == "xgb"
    assert shadow["ranking"]["panel_scoring"]["artifact_path"] == (
        "artifacts/prod/panel-ltr.alpha158_fund.json"
    )


def test_execution_contract_is_explicit() -> None:
    cfg = load_strategy_config(CONFIG_DIR / "strategy_config.json")

    assert cfg["execution"]["enabled"] is True
    assert cfg["execution"]["t2_settlement_days"] == 1
    assert cfg["execution"]["buying_power_mode"] == "non_marginable_buying_power"


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
