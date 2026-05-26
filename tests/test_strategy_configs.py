from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"


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


def test_sector_map_covers_active_watchlist() -> None:
    cfg = _load("strategy_config.json")
    sector_map = cfg.get("sector_map", {})
    missing = sorted(t for t in cfg["watchlist"] if t not in sector_map)
    assert missing == []


def test_strategy_repo_has_no_generated_experiment_configs() -> None:
    generated = sorted(
        p.name for p in CONFIG_DIR.glob("strategy_config.*.json")
        if ".sim_" in p.name or ".codex_" in p.name or ".whatif_" in p.name
    )
    assert generated == []
