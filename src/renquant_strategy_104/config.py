"""Config helpers for the RenQuant 104 strategy repo."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from renquant_common import RegimeLabel, validate_regime_params


def load_strategy_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a strategy config JSON file."""
    cfg_path = Path(path)
    data = json.loads(cfg_path.read_text())
    _validate_strategy_config(data)
    return data


def _validate_strategy_config(data: dict[str, Any]) -> None:
    required = ("watchlist", "regime_params", "sector_map")
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ValueError(f"strategy config missing required keys: {missing}")

    watchlist = data["watchlist"]
    if not isinstance(watchlist, list) or not all(isinstance(t, str) for t in watchlist):
        raise ValueError("strategy config watchlist must be a list of ticker strings")
    duplicates = sorted({t for t in watchlist if watchlist.count(t) > 1})
    if duplicates:
        raise ValueError(f"strategy config watchlist has duplicate tickers: {duplicates}")

    benchmark = data.get("benchmark")
    if benchmark and benchmark not in watchlist:
        raise ValueError(f"strategy benchmark {benchmark!r} must be present in watchlist")

    sector_map = data["sector_map"]
    missing_sector = sorted(t for t in watchlist if t not in sector_map)
    if missing_sector:
        raise ValueError(f"strategy sector_map missing watchlist tickers: {missing_sector}")

    # Closed-set check: every macro RegimeLabel must have a params block.
    # `strict=False` because the legacy strategy_config.json mixes 5 macro
    # regimes + 9 sentiment regimes (HIGH_*/MED_*/LOW_*) under the same key.
    # TODO: split sentiment keys into their own `sentiment_params` block,
    # then flip to strict=True (RFC Open Question #4-adjacent).
    validate_regime_params(data, strict=False)

    bull_calm = data["regime_params"].get(RegimeLabel.BULL_CALM.value, {})
    if bull_calm.get("disable_new_buys") is not False:
        raise ValueError(
            f"{RegimeLabel.BULL_CALM.value} must explicitly keep "
            f"disable_new_buys=false"
        )

    panel = data.get("ranking", {}).get("panel_scoring", {})
    if panel.get("enabled", False):
        _require_relative_path(panel.get("artifact_path"), "ranking.panel_scoring.artifact_path")
        if not panel.get("kind"):
            raise ValueError("ranking.panel_scoring.kind is required when panel scoring is enabled")
        global_cal = panel.get("global_calibration", {})
        if global_cal.get("enabled", False):
            _require_relative_path(
                global_cal.get("artifact_path"),
                "ranking.panel_scoring.global_calibration.artifact_path",
            )

    execution = data.get("execution", {})
    if execution.get("enabled", False):
        if execution.get("t2_settlement_days") not in (1, 2):
            raise ValueError("execution.t2_settlement_days must be 1 or 2")
        valid_modes = {"cash", "settled_cash", "buying_power", "non_marginable_buying_power"}
        mode = execution.get("buying_power_mode")
        if mode not in valid_modes:
            raise ValueError(f"execution.buying_power_mode {mode!r} not in {sorted(valid_modes)}")


def _require_relative_path(raw: Any, field: str) -> None:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{field} is required")
    path = Path(raw)
    if path.is_absolute():
        raise ValueError(f"{field} must be repo-relative, got absolute path {raw!r}")
    if raw.startswith("~"):
        raise ValueError(f"{field} must not use a user-home path: {raw!r}")


def strategy_manifest(path: str | Path) -> dict[str, Any]:
    """Return a fingerprinted manifest for a strategy config file."""
    cfg_path = Path(path)
    data = cfg_path.read_bytes()
    cfg = load_strategy_config(cfg_path)
    return {
        "strategy": "renquant_104",
        "config_name": cfg_path.name,
        "fingerprint": "sha256:" + hashlib.sha256(data).hexdigest(),
        "watchlist_size": len(cfg["watchlist"]),
    }
