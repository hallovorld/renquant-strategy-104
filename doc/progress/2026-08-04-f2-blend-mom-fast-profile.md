# 2026-08-04 — F2 lane profile: zblend(reversal + FAST momentum), dormant at birth

GOAL-9 (orch#794 AC2), operator directive verbatim: "shadow里面应该有…zblend(价
值回归+快动量)". F2 is the fleet's first buildable variant (2 components — the
N_COMPONENTS=2 scorer serves it as-is; F1/F3 wait on the N-generalization).

`configs/strategy_config.shadow_blend_momentum_fast.json` = the S1 slow-blend
profile with EXACTLY two leaf diffs (verified by leaf-wise comparison):
- `components[1].artifact_path` → the FAST ledger
  (`artifacts/momentum_fast/momentum_artifact_ledger.jsonl`), fp pin REMOVED
  and replaced by a v0-precedent bounded `*_pending_first_artifact` marker:
  the fast ledger publishes its genesis 2026-08-08; until then the blend
  loader fail-closes on the absent component (the DESIGNED daily record,
  non-fatal in the Step-5c wrapper). At genesis the SAME change adds the
  measured `expected_config_fingerprint` (momentum-v1_fast-<sha16>) and
  deletes the marker (#793 pattern applied at birth).
- the profile note (lane identity, tag `alpaca_shadow_blend_mom_fast` —
  registered at birth in pipeline#265, before this profile existed).

Not in this PR: the daily_104.sh Step-5c wrapper (RenQuant-side, next PR) —
the profile lands first so the rail gates on a REVIEWED config, the same
lands-before-the-rail order Step 5b used.

Suite: 97 passed / 1 skipped / 1 pre-existing env failure (identical on clean
main).
