# shadow_momentum lane profile — the momentum model's orders get a reviewed home

**Date:** 2026-08-03 · `renquant-strategy-104` · GOAL-7 / pipeline#259 follow-up

STATUS:    DORMANT profile + semantic-pin test. Nothing consumes it until a
           reviewed daily step lands (Step-5-shaped, own READONLY tag);
           serving additionally requires the pipeline#259 surface, merged
           and synced to the siblings today.
WHAT:      configs/strategy_config.shadow_momentum.json = the blend profile
           + EXACTLY three deltas: (1) kind=momentum_residual + the lane's
           digest-chained ledger as artifact_path; (2) the load-bearing
           expected_config_fingerprint pin (momentum-v0-fd65161a20b29314 —
           pipeline#259 fail-closes on absent/mismatched/non-string pins and
           unstamped artifacts); (3) no components. Every delta-6 raw-domain
           null carries over verbatim (uncalibrated z's, same reason).
WHY:       Operator 2026-08-03: "我要看所有shadow，特别是动量模型的下单". The
           rehearsal proved the funnel (4 rounds, final: 84/84 scored,
           ECONOMIC_TRADE, BUY WELL x3 @ $233.10 — coherent with the lane's
           own in-process top3); this PR gives the config a reviewed home so
           the wiring step has something pinned to consume.

EVIDENCE:

```
artifact:      configs/strategy_config.shadow_momentum.json,
               tests/test_strategy_configs.py (SHADOW_PROFILES + pin test)
prod or exp:   DORMANT reviewed surface; no scheduled consumer yet
existing data: rehearsal logs (session scratchpad momentum_rehearsal_*.log);
               momentum health record 2026-08-03: coverage 1.0, 80/80,
               staleness 1d, config_fingerprint momentum-v0-fd65161a20b29314
               [VERIFIED]
scope:         "profile + tests ONLY; no live config, no other profile, no
                script, no job touched. The wash-sale shadow floor lights on
                this lane too (SHADOW_PROFILES membership, tested)."
```

## Wiring path (each its own reviewed change, in order)

1. pipeline: claim a dedicated tag (e.g. alpaca_shadow_momentum) in
   ALLOWED_BROKERS (rehearsals reused the freed alpaca_shadow tag).
2. umbrella: a Step-5-shaped daily step consuming this profile.
3. The blend lane's 20-session observation-window pattern applies here from
   first scheduled green run (same outcomes/guardrails shape).

## Pin-rotation note

expected_config_fingerprint is the PARAMS stamp: weekly content rotation
does NOT move it; a params_version bump does, and then this pin must be
updated in the same reviewed change — the fail-closed mismatch is the
designed reminder.

## Revert

git revert; the profile disappears, nothing consumed it.
