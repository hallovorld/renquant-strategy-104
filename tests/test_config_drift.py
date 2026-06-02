from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from renquant_strategy_104.config_drift import (
    find_drifts,
    resolve_config_root,
    run_check,
)


def _write_configs(root: Path, baseline: dict, live: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "strategy_config.golden.json").write_text(
        json.dumps(baseline),
        encoding="utf-8",
    )
    (root / "strategy_config.json").write_text(json.dumps(live), encoding="utf-8")


def test_find_drifts_flags_boolean_enable() -> None:
    bool_drifts, num_drifts = find_drifts(
        {"ranking": {"gate": {"enabled": False}}},
        {"ranking": {"gate": {"enabled": True}}},
    )

    assert bool_drifts == [
        ("ranking.gate.enabled", "false -> true (flag quietly enabled)"),
    ]
    assert num_drifts == []


def test_default_ignores_skip_recalibrated_fields() -> None:
    bool_drifts, num_drifts = find_drifts(
        {"ranking": {"blend_weights": {"rank": 0.5, "rs": 0.5}}},
        {"ranking": {"blend_weights": {"rank": 0.9, "rs": 0.1}}},
    )

    assert bool_drifts == []
    assert num_drifts == []


def test_run_check_returns_zero_when_configs_match(tmp_path: Path) -> None:
    cfg = {"watchlist": ["AAPL"], "ranking": {"gate": {"enabled": False}}}
    _write_configs(tmp_path, cfg, cfg)

    code, message = run_check(
        config_root=tmp_path,
        baseline_name="strategy_config.golden.json",
        live_name="strategy_config.json",
        numeric_tolerance=0.10,
        ignore_paths=set(),
        use_default_ignores=True,
    )

    assert code == 0
    assert "Config drift check OK" in message


def test_resolve_config_root_prefers_umbrella_strategy_dir(tmp_path: Path) -> None:
    strategy_dir = tmp_path / "backtesting" / "renquant_104"
    strategy_dir.mkdir(parents=True)

    assert (
        resolve_config_root(
            repo_root=tmp_path,
            strategy="renquant_104",
            config_root=None,
        )
        == strategy_dir
    )


def test_config_drift_cli_exposes_repo_root() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "renquant_strategy_104.config_drift", "--help"],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "--repo-root" in proc.stdout
    assert "RENQUANT_REPO_ROOT" in proc.stdout
