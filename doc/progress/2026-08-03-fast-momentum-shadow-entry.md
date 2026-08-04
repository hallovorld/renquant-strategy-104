# `momentum_fast_v1_shadow` shadow_models entry — dormant-safe, pending first publish (model#199 item 3)

**Date:** 2026-08-03 · `renquant-strategy-104` · GOAL-8 fast arm

STATUS:    config entry + test pins ONLY, declared PENDING by name. The lane
           serves nothing until (a) the orchestrator wrapper's fast train
           step (#199 item 2) is deployed on the run surface, (b) a Saturday
           firing publishes the first fast ledger, and (c) the umbrella s104
           pin advances past this PR.
WHAT:      `configs/strategy_config.json` + `configs/strategy_config.golden.json`
           (lockstep, semantic-match contract): `ranking.panel_scoring.shadow_models`
           gains `momentum_fast_v1_shadow` — kind `momentum_residual`,
           artifact_path `artifacts/momentum_fast/momentum_artifact_ledger.jsonl`,
           field shape mirroring the v0 entry exactly (no
           expected_content_sha256 / expected_config_fingerprint — the v0
           ledger-pointer entry carries none; the ledger chain + the loader's
           content-sha and cross-field checks are the identity surface).
           The entry carries `_2026_08_03_pending_first_artifact`, bounded by
           the named `PENDING_FIRST_ARTIFACT` set in
           `tests/test_strategy_configs.py` (the v0 precedent: declared in the
           #77 era, retired in #78 after the first publish).
DORMANT BEHAVIOR (read from pipeline shadow_scoring/momentum_residual_scorer,
           not asserted): while the fast ledger does not exist, the daily
           record for this lane is the unresolved-artifact NOT-LOADED record —
           `artifact_resolved: false`, `load_error: "artifact_path ... did not
           resolve to an existing file"` — NOT the `not_yet_published`
           expected skip, which requires an existing chain-verified ZERO-ROW
           ledger. Fault-class recording of a declared pending lane is the
           designed reminder that the config reached the run surface before
           its producer; the bounded set + entry key carry the declaration.
WHY:       model#199 build order item 3: the fast lane (63/5, frozen in #199,
           kind `momentum_residual_v1_fast` per #200) rides the existing
           momentum serving handler for the operator's daily fast-momentum
           patrol; shadow = data collection, no verdict claimed.

Tests: the full shadow_models literal (prod==golden) gains the entry verbatim;
`PENDING_FIRST_ARTIFACT = {"momentum_fast_v1_shadow"}`; the momentum
ledger-path pin test now covers BOTH lanes and additionally pins that the two
lanes name DISTINCT sibling directories (one ledger tail per lane — a shared
ledger would alternate lanes week to week).

EVIDENCE:

```
tests:  96 passed / 1 skipped / 1 failed, full suite, this worktree.
        The single failure (test_config_drift.py::
        test_config_drift_cli_exposes_repo_root) fails IDENTICALLY on a
        clean origin/main worktree — pre-existing environment failure
        (python -m renquant_strategy_104.config_drift not importable under
        the RenQuant venv on this machine), not introduced here.
        [VERIFIED — both runs this session]
scope:  "two lockstep configs + one test file + this doc; no profile files,
         no scripts, no pins, nothing deployed."
```

## Follow-up (post-first-publish, its own PR)

Delete `_2026_08_03_pending_first_artifact` and shrink
`PENDING_FIRST_ARTIFACT` back to empty in the SAME change (the #78 precedent).

## Revert

git revert; the entry is additive and the lane is dormant until deployed.
