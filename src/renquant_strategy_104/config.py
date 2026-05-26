"""Config helpers for the RenQuant 104 strategy repo."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_strategy_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a strategy config JSON file."""
    cfg_path = Path(path)
    data = json.loads(cfg_path.read_text())
    required = ("watchlist", "regime_params", "sector_map")
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ValueError(f"strategy config missing required keys: {missing}")
    return data


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

