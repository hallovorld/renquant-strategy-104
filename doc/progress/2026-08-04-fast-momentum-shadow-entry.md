# Fast-momentum shadow entry — the daily patrol lane's config home (model#199 item 3)

**Date:** 2026-08-04 · `renquant-strategy-104` · GOAL-8 fast arm

STATUS:    DORMANT-BY-DECLARATION: the entry lands with a BOUNDED
           pending-first-artifact marker (the v0/#78 precedent) — nothing
           publishes artifacts/momentum_fast/ until the orchestrator
           wrapper's second train step (#199 item 2) deploys AND a Saturday
           firing runs the fast lane.
WHAT:      `momentum_fast_v1_shadow` added to shadow_models in BOTH
           strategy_config.json and golden (lockstep): kind
           momentum_residual, its OWN ledger path, entry notes carrying the
           frozen 63/5 clock (#199), the kind-derivation contract (#200),
           and the shared-basename constraint (the pipeline loader hardcodes
           momentum_residual_v0.json; identity = kind/params_version/sha —
           model#201's measured decision, mirrored here). PENDING_FIRST_
           ARTIFACT gains the name; the marker documents the honest pending
           semantics: an unresolved artifact is the NOT-LOADED record, NOT
           the not_yet_published expected skip (that requires an existing
           chain-verified zero-row ledger).
WHY/DIR:   Operator 2026-08-03: a fast-momentum shadow patrol whose top-3
           lands in the DAILY primary ntfy with zero new job/push surface.
           This entry is what makes the in-process serving pick the lane up
           the day its first artifact exists.

EVIDENCE:

```
artifact:      configs/strategy_config.json + golden (lockstep),
               tests/test_strategy_configs.py (PENDING_FIRST_ARTIFACT
               bounded set + lane-count pins)
prod or exp:   prod config's shadow_models (data collection only; no
               scoring behaviour until the lane's artifact exists)
existing data: both configs parse and carry the three-lane set
               [clf, momentum_v0, momentum_fast]; suite 96 passed + only
               the pre-existing machine-path failure
               (test_config_drift_cli_exposes_repo_root, red on origin/main
               identically).  [VERIFIED — reviewed and re-run by the
               session driver; original build delegated]
best-known?:   NOT APPLICABLE — no model comparison is claimed; the lane is
               declared, not evaluated.
scope:         "two configs + the pin test + this doc; NO wrapper change
                (item 2's orchestrator half is its own PR), NO pipeline
                change, nothing published."
```

NEXT:      (1) orchestrator wrapper PR (second non-fatal train step) +
           model#201 (CLI half, in review); (2) after the first Saturday
           fast publish: delete the entry's pending key + shrink
           PENDING_FIRST_ARTIFACT to empty in the same change (the #78
           precedent); (3) the daily ntfy then carries
           SHADOW[momentum_fast_v1] top3 automatically.

## Revert

git revert + dual s104 sync; the daily shadow task stops looking for the
lane.
