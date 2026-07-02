"""Offline link-check for doc/strategy-map.md via doc/strategy-map-pointers.json.

Honest scope (the previous revision's docstring overclaimed):

1. LOCAL, always run — the manifest itself is enforced: every backticked
   cross-repo path in the doc's prose must be registered in the manifest
   (repo/path/ownership), every pointer/config key OWNED BY THIS REPO must
   resolve locally, and the doc must not hand-copy live config values.
2. INTEGRATION, opt-in — with RENQUANT_POINTER_INTEGRATION=1 (set by the
   umbrella integration job after syncing the canonical sibling checkouts of
   RENQUANT_REPOS.md to their pins/main), every cross-repo pointer is
   asserted to resolve inside its owning sibling checkout. Without the flag
   the check SKIPS loudly; it never fakes a pass and never touches the
   network. The gate is deliberate: sibling working trees on an arbitrary
   feature branch are NOT the canonical state (merged-is-not-deployed), so
   auto-engaging on mere directory presence would fail for reasons that are
   not pointer rot.

Cross-repo existence on a unit-test box is instead anchored by the manifest
itself: it records the owning repo's main SHA at last verification, giving
every pointer an immutable permalink form a reviewer can audit offline.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
THIS_REPO = "renquant-strategy-104"
STRATEGY_MAP = REPO_ROOT / "doc" / "strategy-map.md"
MANIFEST = REPO_ROOT / "doc" / "strategy-map-pointers.json"
STRATEGY_CONFIG = REPO_ROOT / "configs" / "strategy_config.json"

# A backticked token counts as a path pointer when it has at least one "/"
# and looks like a repo file/dir reference (extension we point at, or a
# trailing "/" for directories).
_PATH_TOKEN = re.compile(r"[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+/?")
_PATH_SUFFIXES = (".md", ".py", ".json", "/")


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def _backticked_path_tokens(text: str) -> set[str]:
    tokens = set()
    for span in re.findall(r"`([^`]+)`", text):
        if _PATH_TOKEN.fullmatch(span) and span.endswith(_PATH_SUFFIXES):
            tokens.add(span)
    return tokens


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


def test_strategy_map_and_manifest_exist():
    assert STRATEGY_MAP.exists(), "doc/strategy-map.md must exist"
    assert MANIFEST.exists(), "doc/strategy-map-pointers.json must exist"


def test_every_backticked_path_in_prose_is_registered_in_manifest():
    """The reviewable contract: the prose cannot name a cross-repo path that
    the machine-readable manifest does not know about. Doc tokens may be
    repo-prefixed (`RenQuant/doc/...`) or repo-relative (`doc/...`)."""
    manifest = _manifest()
    registered = set()
    for entry in manifest["pointers"]:
        registered.add(entry["path"])
        registered.add(f"{entry['repo']}/{entry['path']}")
    missing = sorted(_backticked_path_tokens(STRATEGY_MAP.read_text()) - registered)
    assert not missing, (
        "backticked path(s) in doc/strategy-map.md are not registered in "
        f"doc/strategy-map-pointers.json: {missing} — register them with "
        "repo/path/ownership (or fix the prose)"
    )


def test_manifest_entries_have_repo_path_ownership():
    for entry in _manifest()["pointers"]:
        for field in ("repo", "path", "ownership"):
            assert entry.get(field), f"manifest entry missing '{field}': {entry}"


def test_pointers_owned_by_this_repo_resolve_locally():
    for entry in _manifest()["pointers"]:
        if entry["repo"] != THIS_REPO:
            continue
        target = REPO_ROOT / entry["path"]
        assert target.exists(), (
            f"manifest claims this repo owns '{entry['path']}' but it does not "
            f"exist — the pointer has rotted"
        )


def test_cross_repo_pointers_resolve_in_sibling_checkouts_when_declared():
    """Integration mode, opt-in via RENQUANT_POINTER_INTEGRATION=1: the
    integration job syncs RENQUANT_REPOS.md's sibling checkouts to their
    canonical state, then sets the flag — from that point a missing checkout
    or a missing path is a hard failure (pointer rot or a broken layout).
    Without the flag: skip loudly, never fake a pass, never fetch. Working
    trees on arbitrary local branches are not canonical, so presence of a
    sibling directory alone is NOT enough to engage this assertion."""
    if os.environ.get("RENQUANT_POINTER_INTEGRATION") != "1":
        pytest.skip(
            "RENQUANT_POINTER_INTEGRATION != 1 — cross-repo pointer existence "
            "is asserted only in the integration layout (siblings synced to "
            "canonical state); offline anchor = the verified main SHAs "
            "recorded in doc/strategy-map-pointers.json"
        )
    problems = []
    for entry in _manifest()["pointers"]:
        if entry["repo"] == THIS_REPO:
            continue
        checkout = REPO_ROOT.parent / entry["repo"]
        if not checkout.is_dir():
            problems.append(f"missing sibling checkout: {entry['repo']}")
        elif not (checkout / entry["path"]).exists():
            problems.append(f"pointer rotted: {entry['repo']}/{entry['path']}")
    assert not problems, (
        "cross-repo pointer validation failed in integration layout: "
        f"{sorted(set(problems))}"
    )


def test_every_owned_config_key_resolves_in_strategy_config():
    config = json.loads(STRATEGY_CONFIG.read_text())
    for dotted_key in _manifest()["owned_config_keys"]:
        _resolve_dotted(config, dotted_key)


def test_strategy_map_names_every_owned_key_by_leaf_name():
    """Keeps the manifest's owned_config_keys honest against the prose: if
    §4 drops a key name, the manifest (not an independently invented list)
    must be updated in the same change."""
    text = STRATEGY_MAP.read_text()
    for dotted_key in _manifest()["owned_config_keys"]:
        leaf = dotted_key.rsplit(".", 1)[-1]
        assert re.search(rf"`{re.escape(leaf)}`", text), (
            f"strategy-map.md no longer mentions `{leaf}` by name in §4 — "
            f"either update owned_config_keys in the manifest or restore the "
            f"doc's reference"
        )


def test_strategy_map_does_not_hand_copy_numeric_config_values():
    """The doc's own STATUS line says numbers are never copied in by hand.
    Regression-guard for the exact class the review found: a live numeric
    value from strategy_config.json restated next to its key name."""
    text = STRATEGY_MAP.read_text()
    config = json.loads(STRATEGY_CONFIG.read_text())
    live_mu_floor = _resolve_dotted(config, "ranking.panel_scoring.conviction_gate.mu_floor")
    live_top_n = _resolve_dotted(config, "rotation.panel_buy_top_n")
    assert f"mu_floor {live_mu_floor}" not in text
    assert f"panel_buy_top_n` ({live_top_n};" not in text
