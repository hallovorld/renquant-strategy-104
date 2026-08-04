# 2026-08-04 — strategy_config.shadow_blend_momentum.json (GOAL-8 S1 lane profile)

STATUS:    profile + mirrored semantic-pin test; merge does NOT deploy
           (activation = the umbrella pin batch that follows RQ#563)
WHAT:      the S1 z(prod)+z(slow momentum) profile, generated from the
           certified shadow_blend profile with EXACTLY one difference —
           component 1 is the momentum ledger-pointer leg (pipeline#261
           kind dispatch): kind=momentum_residual, the prod config's own
           slow-momentum ledger path (single-source asserted), NO
           expected_content_sha256 (append-only ledger — pipeline#261
           refuses a byte pin), expected_config_fingerprint =
           momentum-v0-fd65161a20b29314 (loader-stamped params
           fingerprint, measured 2026-08-04 from the live genesis ledger
           tail: cutoff 2026-08-02, artifact a824c480, n_scored 144).
           Same six deltas vs production as the clf blend; the mirrored
           test additionally normalizes both blend profiles down to
           component-1-popped and asserts full equality — the two lanes
           are the same construction differing only in that leg.
WHY/DIR:   GOAL-8 S1 per the FROZEN prereg (renquant-orchestrator
           doc/research/2026-08-04-goal8-s1-zblend-prereg.md, merged
           orch#777): profile reviewed AGAINST the frozen bar. Consumer =
           daily_104.sh Step 5b (RQ#563, tag alpaca_shadow_blend_mom),
           dormant until this file reaches the PINNED configs. The
           20-session S1 clock starts at the first scheduled session
           after the verified runtime-sync deployment boundary; that
           sync's timestamp + shas go in the deployment record when the
           pin batch lands — NOT at this PR's merge.
EVIDENCE:  tests/test_strategy_configs.py 39 passed (new mirror test +
           enumeration); full make test 98 passed / 1 skipped.
NEXT:      RQ#563 merge → umbrella pin batch (s104 pin + pipeline
           3ecd9880) → live pull + runtime sync (the recorded boundary) →
           S1 clock starts next scheduled session.
