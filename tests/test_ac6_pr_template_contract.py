"""The AC6 review surface must not vanish silently. (GOAL-5 AC6 R2)

A PR-template checklist item is the weakest control in the programme: nothing runs it,
and it can be deleted in a one-line diff no test notices. That is exactly why it gets a
test.

These do NOT claim the rule is enforced. They claim the review surface is present and
says what it must — which is the whole of what R2 delivers.
"""

from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = REPO / ".github" / "pull_request_template.md"


def test_the_pr_template_exists():
    assert TEMPLATE.is_file(), (
        "the AC6 review surface is the PR template; if it is gone, R2 is gone")


def test_it_carries_the_AC6_gate_design_item():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "GOAL-5 AC6" in text and "governed override path" in text


def test_it_names_all_THREE_required_properties():
    text = TEMPLATE.read_text(encoding="utf-8").lower()
    for prop in ("identity", "expiry", "binding"):
        assert f"**{prop}**" in text, prop


def test_it_says_a_CONFIG_EDIT_is_in_scope():
    """The repo-specific half, and the one that decides whether this item ever fires
    here. This repo holds 1 gate-code file out of 8 Python files, so a code-shaped
    reading of 'does this PR add a gate?' answers no almost always — while the threshold
    values that pipeline's gates read live in configs/."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "CONFIG VALUE" in text
    assert "strategy_config" in text
    assert "gate\n      change in effect" in text or "gate change in effect" in text \
        or "gate\n      change" in text


def test_it_names_the_three_config_shapes_that_count():
    """A threshold, a cap and an enablement flag. Naming only 'threshold' would let a
    flag flip past."""
    text = TEMPLATE.read_text(encoding="utf-8").lower()
    for shape in ("veto\n      threshold", "cap", "_enabled"):
        assert shape.replace("\n      ", " ") in " ".join(text.split()), shape


def test_it_REFUSES_temporary_as_an_expiry():
    assert '"Temporary" is not an expiry' in TEMPLATE.read_text(encoding="utf-8")


def test_it_points_at_the_CANONICAL_rule_not_a_local_paraphrase():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "subrepo-operating-model.md" in text
    assert "2026-07-20-ac6-gate-design-rule.md" in text


def test_it_states_that_this_is_NOT_enforcement():
    assert "review surface, not enforcement" in TEMPLATE.read_text(encoding="utf-8")
