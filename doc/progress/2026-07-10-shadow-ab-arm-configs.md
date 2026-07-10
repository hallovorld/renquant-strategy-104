# D6-§2a two-arm shadow A/B — config-only treatment PR (the #52 successor)   (PR #53)

STATUS:    delivered
WHAT:      Adds the two D6-§2a shadow-arm configs as DEDICATED new files
           (`shadow_a.json` treatment, `shadow_b.json` control), differing
           in exactly one functional key (`buy_floor_std_mult`), pinned
           three ways (line/tree/byte). The pre-existing legacy
           `shadow.json` (Step-4 ops shadow, broker tag `alpaca_shadow`)
           stays byte-identical — it is NOT one of the experiment's arms.
           Config-only — no arming, no scheduling, nothing on the live book.
WHY/DIR:   The #52 successor Codex prescribed: protocol to orchestrator
           first (done, #443 merged), then the strategy config treatment
           alone. Binding contract is orchestrator main's merged
           `doc/design/2026-07-09-governor-prereg-replay-protocol.md` §2a
           @ `8981edfa2a2ef71f538bac5b965bc389f21a9eb7` — this repo only
           materializes it.
EVIDENCE:  n/a (config/test-only change, not a model/data claim — see
           "Contract robustness" below for the pin-test evidence)
NEXT:      P-1 (renquant-execution readonly-broker parameterization,
           merged) and P-2 (orchestrator#451 two-arm runner, decision-
           snapshot digest / freeze-payload / config-diff-assertion /
           umbrella-dependency fixes now pushed, pending fresh Codex
           re-review) before the experiment can start.

## Correction (2026-07-10, same day — Codex review on the first head)

The first version of this PR mutated `configs/strategy_config.shadow.json`
IN PLACE to the 0.5σ treatment values. Codex caught a real safety problem:
that file is the LEGACY Step-4 ops shadow config, still read daily by
`daily_104.sh`'s existing single-arm shadow invocation (broker tag
`alpaca_shadow`) — independent of, and unaware of, the D6-§2a experiment.
Mutating it in place would have silently re-armed the legacy shadow with
an uncontrolled 0.5σ treatment observation *before* P-2 isolates the two
new experiment arms onto their own tags (`alpaca_shadow_a`/`_b`),
contaminating the very paired comparison this protocol exists to run
cleanly.

**Fix**: the treatment arm now lives in its own new file,
`configs/strategy_config.shadow_a.json` — never a mutation of the legacy
`shadow.json`, which is restored to and pinned at its pre-PR values
(`adaptive_quantile`, `buy_floor_std_mult=1`, no `_arm` annotation, no
reference to the §2a protocol). A new test,
`test_legacy_shadow_config_untouched_by_shadow_ab`, makes this loud in CI.

## Bottom line

Created the two §2a arm configs, exactly per the MERGED protocol
(`doc/design/2026-07-09-governor-prereg-replay-protocol.md` §2a on
renquant-orchestrator main @ `8981edfa2a2ef71f538bac5b965bc389f21a9eb7`,
the merge commit of orchestrator #443 — the doc is the BINDING contract,
this repo only materializes it):

- **Arm S-0.5 (TREATMENT)** = `configs/strategy_config.shadow_a.json` (NEW),
  frozen §2a values: `buy_floor` `adaptive_mean_std`, `buy_floor_std_mult
  = 0.5`. Broker-state tag `alpaca_shadow_a` (runner-threaded, NOT a
  config key).
- **Arm S-1.0 (CONTROL)** = `configs/strategy_config.shadow_b.json` (NEW), a
  line-for-line clone of the treatment arm differing in EXACTLY ONE
  functional key: `buy_floor_std_mult = 1` (production's floor multiple),
  plus the inert `_arm` annotation string. Broker-state tag
  `alpaca_shadow_b` (runner-threaded, NOT a config key).
- **Legacy `configs/strategy_config.shadow.json`** is untouched — pinned at
  its pre-experiment values and carries no §2a annotation.

Exact full diff between the two arm files (pin-enforced three ways —
line-level, parsed-tree, canonical-bytes):

| Path | shadow_a.json (S-0.5) | shadow_b.json (S-1.0) |
|---|---|---|
| `ranking.panel_scoring.buy_floor_std_mult` | `0.5` | `1` |
| `ranking.panel_scoring._arm` (inert annotation) | S-0.5 TREATMENT / tag `alpaca_shadow_a` | S-1.0 CONTROL / tag `alpaca_shadow_b` |

## Why the shadow config flips here (and prod/golden/legacy-shadow do not)

§2a normatively freezes the S-0.5 arm's values (`buy_floor =
"adaptive_mean_std"`, `buy_floor_std_mult = 0.5` — "frozen values restated
here NORMATIVELY (this doc, not `strategy-104#52`, is the contract)") and
defines this PR as "the #52 successor: `strategy_config.shadow_b.json` +
config-drift pin test verifying prod/golden untouched and shadow_b
differing from [the treatment arm] in EXACTLY the one frozen treatment
key, `buy_floor_std_mult`". Closed PR #52's Codex review prescribed exactly
this sequencing: protocol to orchestrator first, "then submit the strategy
config treatment alone." The treatment arm needs `adaptive_mean_std` mode
because `buy_floor_std_mult` is dead config under `adaptive_quantile` (the
deployed-but-dark non-experiment #52's own body warned about) — but that
mode flip belongs in a DEDICATED new file, not a mutation of the legacy
shadow config that's still live-invoked outside this experiment.

Production and golden are byte-untouched; the new
`test_shadow_ab_leaves_prod_and_golden_at_production_baseline` pins them at
the production baseline (XGB, `adaptive_mean_std` @ 1.0σ, Kelly 0.3/0.12,
BULL_CALM 0.12, one-share floor OFF) on every §2a-relevant key. The legacy
shadow config is likewise byte-untouched; `test_legacy_shadow_config_
untouched_by_shadow_ab` pins it at its pre-PR `adaptive_quantile` /
`buy_floor_std_mult=1` values with no `_arm` annotation.

The 2026-06-11 `adaptive_quantile` history (mean_std shape-instability on
Platt-compressed PatchTST scores) is preserved in the rewritten
`_buy_floor_reason` (identical text in both arm files) and registered by
§2a as the estimand-(B) scorer-transfer diagnostic; the σ-multiplier
treatment is scale-free per-session, which mitigates but does not
eliminate it.

## What is NOT in this PR (deliberately)

- **No arming, no scheduling**: no launchd entry, no `daily_104.sh` change,
  no runner. Invocation is P-2's separately-gated step (orchestrator #451,
  under its own review contract frozen in §2a).
- **No mutation of the legacy shadow path**: `configs/strategy_config.
  shadow.json` (broker tag `alpaca_shadow`, Step-4 ops shadow) is untouched
  and carries no reference to this experiment — see "Correction" above.
- **No broker-state tag keys**: `alpaca_shadow_a`/`alpaca_shadow_b` are
  threaded by the P-2 two-arm runner into
  `ReadOnlyBrokerWrapper(broker_name=<tag>)` + pipeline `state_paths`; the
  legacy `alpaca_shadow` Step-4 ops shadow keeps its tag and state untouched.
- **No preflight shim**: §2a WITHDRAWS the r5 `live.preflight.strict=false`
  second config key; arm-symmetric preflight is P-2-owned. The pin test
  asserts no `live` section exists in either arm.
- **No live enablement**: flipping PRODUCTION `buy_floor_std_mult` is a
  separate future PR carrying the §2a Tier-2 verdict memo + pre-registration
  gate + Codex review. Neither the protocol nor this PR authorizes anything
  on the live book.

## Contract robustness

§2a's treatment-fingerprint drift rule: if either arm's resolved config hash
changes mid-run, the experiment is VOID and restarts under a new protocol
version — so later config PRs cannot reinterpret the experiment, only
terminate it. The pin tests make any drift loud in CI as well, including
drift of the legacy shadow config back toward the experiment's values.

## Changes

- `configs/strategy_config.shadow.json` — restored to byte-identical with
  its pre-PR (legacy, `origin/main`) content; NOT part of this experiment
- `configs/strategy_config.shadow_a.json` — NEW S-0.5 treatment arm (clone
  of the pre-correction shadow.json content, moved to its own dedicated
  file)
- `configs/strategy_config.shadow_b.json` — NEW S-1.0 control arm (clone;
  single functional delta from shadow_a.json)
- `tests/test_strategy_configs.py` — 4 new pin tests
  (`test_shadow_ab_arm_configs_carry_frozen_2a_values`,
  `test_shadow_ab_arms_differ_in_exactly_the_treatment_key`,
  `test_shadow_ab_leaves_prod_and_golden_at_production_baseline`,
  `test_legacy_shadow_config_untouched_by_shadow_ab`) + shadow_a/shadow_b
  added to the required-configs parse test

## Next steps (outside this PR)

1. P-1 — renquant-execution readonly-broker parameterization (+ behavior pins) — MERGED
2. P-2 — orchestrator two-arm shadow runner #451 (its §2a review contract:
   shared decision-snapshot digest, distinct state paths, no umbrella import,
   pair-fail-closed) — fixes pushed, pending fresh Codex re-review
3. Experiment start only after BOTH merge + fresh empty `alpaca_shadow_a`/`_b`
   state; fingerprints frozen at start per §2a run-bundle rules
