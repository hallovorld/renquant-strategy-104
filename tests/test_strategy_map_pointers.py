"""Link-check for doc/strategy-map.md's cross-repo/config pointers.

RS-104's strategy-map is deliberately a POINTER document (no hand-copied
numbers, per its own STATUS line) — the failure mode this test guards
against is a pointer silently rotting: the doc names a config key or a
cross-repo doc that no longer exists, and nobody notices because the doc
itself renders fine either way.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_MAP = REPO_ROOT / "doc" / "strategy-map.md"
STRATEGY_CONFIG = REPO_ROOT / "configs" / "strategy_config.json"

# Every config key doc/strategy-map.md §4 names as "owned here" — each must
# genuinely resolve inside configs/strategy_config.json. Update this list
# whenever the doc's §4 key list changes.
CLAIMED_CONFIG_KEYS = [
    "ranking.panel_scoring.conviction_gate.mu_floor",
    "rotation.panel_buy_top_n",
    "rotation.joint_actions.qp_cash_drag_lambda",
    "regime_params.BULL_CALM",
    "model_staleness_days",
]


def _resolve_dotted(config: dict, dotted_key: str):
    node = config
    for part in dotted_key.split("."):
        assert isinstance(node, dict), (
            f"{dotted_key}: path segment before '{part}' is not a dict "
            f"(pointer no longer resolves — config shape changed)"
        )
        assert part in node, (
            f"{dotted_key}: key '{part}' not found — the strategy-map pointer "
            f"has rotted, config no longer has this key"
        )
        node = node[part]
    return node


def test_strategy_map_exists():
    assert STRATEGY_MAP.exists(), "doc/strategy-map.md must exist"


def test_every_claimed_config_key_resolves_in_strategy_config():
    config = json.loads(STRATEGY_CONFIG.read_text())
    for dotted_key in CLAIMED_CONFIG_KEYS:
        _resolve_dotted(config, dotted_key)


def test_strategy_map_names_every_claimed_key_by_leaf_name():
    """Cheap drift guard the other direction: if the doc's §4 prose drops a
    key name entirely (rather than the config losing it), this test alone
    won't catch a genuinely stale doc, but it does prove the CLAIMED_CONFIG_KEYS
    fixture above is actually kept in sync with what the doc names, not a
    list invented independently of the prose."""
    text = STRATEGY_MAP.read_text()
    for dotted_key in CLAIMED_CONFIG_KEYS:
        leaf = dotted_key.rsplit(".", 1)[-1]
        assert re.search(rf"`{re.escape(leaf)}`", text), (
            f"strategy-map.md no longer mentions `{leaf}` by name in §4 — "
            f"either update CLAIMED_CONFIG_KEYS in this test or restore the "
            f"doc's reference"
        )


def test_strategy_map_does_not_hand_copy_numeric_config_values():
    """The doc's own STATUS line says 'do not copy numbers into here by
    hand.' Regression-guard against the exact class of value this review
    round found copied: a live numeric value from strategy_config.json
    appearing verbatim next to one of the claimed key names in §4."""
    text = STRATEGY_MAP.read_text()
    config = json.loads(STRATEGY_CONFIG.read_text())
    live_mu_floor = _resolve_dotted(config, "ranking.panel_scoring.conviction_gate.mu_floor")
    live_top_n = _resolve_dotted(config, "rotation.panel_buy_top_n")
    # These specific values (0.03, 3) were the ones found hand-copied into
    # the doc in the reviewed round — assert they no longer appear stated
    # as bare parenthetical values next to the key names.
    assert f"mu_floor {live_mu_floor}" not in text
    assert f"panel_buy_top_n` ({live_top_n};" not in text
