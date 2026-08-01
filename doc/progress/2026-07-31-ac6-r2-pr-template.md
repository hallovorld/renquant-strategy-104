# GOAL-5 AC6 R2 — the last repo, and the easiest place in the programme to miss a gate

**Date:** 2026-07-31 · `renquant-strategy-104` · GOAL-5 (P0) / AC6 R2, tracked in
`renquant-orchestrator`#564

## Why this repo is the awkward one

Measured here `[本次实测 2026-07-31]`:

| | |
|---|---:|
| Python files matching `admission\|_veto\|sell_only\|hard.?gate\|fail.?closed` | **1** |
| Python files in the repo, total | **8** |
| `configs/strategy_config*.json` carrying gate thresholds | **6** |

So a **code-shaped** reading of *"does this PR add a hard gate?"* answers **no** almost
always — and the answer is misleading. The threshold values that `renquant-pipeline`'s
gates read live in `configs/`. **Tightening a veto threshold, lowering a cap, or flipping
an `*_enabled` flag here is a gate change in effect, executed by code in another repo.**

That is the easiest place in the programme to miss a gate: the file that changes has no
gate in it, and the file with the gate does not change.

The template says so, and a test asserts it — naming all three config shapes, because
naming only "threshold" would let a flag flip past.

## The rule is delegated, not copied

Canonical statement stays in Universal Rule §7 and the orchestrator design doc. A per-repo
paraphrase drifts from the rule it paraphrases; only the **repo-specific application**
is written locally.

## What it is NOT — stated on the template

> *This checklist item is a review surface, not enforcement.*

Measured: `renquant-orchestrator`#690 established the shared `LiveRunBundle` schema
declares **7** fields and silently drops the rest, so a provenance field added to that path
would be validated by nothing `[早前实测 2026-07-31, orch#690]`. Until R4 closes, this item
and the reviewer reading it *are* the gate.

## Tests

8. Existence; the AC6 item; all three properties (*identity*, *expiry*, *binding*); **a
config edit is in scope**; **all three config shapes named** — threshold, cap, `_enabled`;
**"Temporary" refused** as an expiry; a pointer to the canonical rule; and the
not-enforcement line.

Suite: **93 passed, 1 skipped, 1 failed**. That failure —
`test_config_drift.py::test_config_drift_cli_exposes_repo_root`, a `python -m
renquant_strategy_104.config_drift --help` subprocess exiting 1 — **pre-exists this
branch**, verified by stashing these changes and re-running it, where it fails identically.
It is a worktree import-path condition, not a code defect this branch introduces.

## R2 is now complete

**4 of 4 repos**: `renquant-orchestrator` (earlier), `renquant-pipeline` (#241),
`renquant-execution` (#39), and this one. **R4 remains blocked, not pending** — closing it
needs `extra="forbid"` plus declared fields, or a purpose-built daily-bundle contract, and
that is a shared-contract change across repos.
