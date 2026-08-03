# shadow_blend lane STRUCTURAL_BLOCK fixed — raw-z coherence (delta 6)

**Date:** 2026-08-03 · `renquant-strategy-104` · 104-repair directive

STATUS:    config + test; rehearsed end-to-end against the live readonly
           broker BEFORE this PR (evidence below). Deploys via the runtime
           strategy-104 checkout sync (granted playbook) — merged ≠ live
           until that sync.
WHAT:      Adds delta 6 to strategy_config.shadow_blend.json: every absolute
           probability-domain threshold nulled/disabled (buy_floor,
           model_sell.panel_veto, rotation floors, qp_admission_gate rank/ER
           floors). Admission for the lane becomes ordinal-only (top_n,
           slots, risk gates) + legacy sizing. test pins each knob.
WHY:       The 2026-08-02 pipeline pin deployed the rank_score domain guard:
           any buy_floor mode fail-closes when calibration did not run. This
           lane is uncalibrated BY DESIGN (delta 2: the prod calibrator can
           never match the blend composite fingerprint), so on 2026-08-03 the
           guard emptied all 87 candidates and flipped the lane
           STRUCTURAL_BLOCK (`panel_scoring_fail_closed(87)`).

EVIDENCE:

```
artifact:      configs/strategy_config.shadow_blend.json,
               tests/test_strategy_configs.py (delta-6 pins + normalization)
prod or exp:   prod-adjacent — a READONLY shadow lane's reviewed profile;
               live buy path untouched
existing data: logs/daily_104/2026-08-03_shadow_blend.log:
               "VetoWeakBuysTask: rank_score is in the RAW score domain
               (calibration did not run) but the buy floor 1.5221 ... is a
               probability-domain threshold — refusing" →
               "no trade (panel_scoring_fail_closed(87))", verdict
               STRUCTURAL_BLOCK.  Runs 07-29/30/31 'passed' only because raw
               z's were compared against probability constants pre-guard
               (07-30: floor 1.457 on Σz, 11/83 admitted).  [VERIFIED]
rehearsal:     full e2e readonly run with THIS config (RENQUANT_READONLY_TAG=
               alpaca_shadow_blend, same invocation as daily Step 5):
               rc=0, panel_state=scored, 145 scored, admission shadow
               added=25 dropped=0, 2 shadow buys (AMZN x1 @284.02,
               ZM x4 @98.25), verdict DEGRADED fired=1 (the known one-share
               floor invariant, orch#608 — unrelated to this lane's fix),
               decision trace integrity OK, state isolated to
               live_state.alpaca_shadow_blend.json.
               [VERIFIED — run 2026-08-03 16:22 PT, log preserved in the
               session scratchpad blend_rehearsal_20260803.log]
scope:         "this is the shadow_blend profile + its semantic-pin test
                ONLY; strategy_config.json (live) and every other profile are
                byte-identical."
```

## The six declared deltas (was five)

Delta 6 (new): raw-z-domain coherence. The lane's rank_score is a raw
z-composite; absolute probability constants (buy_floor min/cap, panel_veto
0.5, rotation 0.3/0.2, qp gate 0.55/ER map) are unit-mismatched there. Each
is nulled/disabled with an inline `_shadow_blend_*_note`; the semantic-pin
test asserts every one so a merge-back from prod cannot silently re-arm a
fail-close. A missing calibrator ER is a REFUSAL on the current pin
(`qp_admission_expected_return`), so `min_expected_return_by_regime` must be
null here, not merely unlisted.

## Deliberately NOT done

- No calibrator fitted for the composite. That is the durable path back to a
  FLOORED blend lane (fit + stamp against the blend composite fingerprint,
  renquant-model territory) and is tracked as a follow-up; until then the
  lane measures ranking-driven funnel differences, which is its purpose.
- `kelly_sizing.use_calibrator_mu` left verbatim-true: kelly_sizing.enabled
  is false in this lane (delta 4) and the verbatim value preserves
  diff-ability against prod — reverted an over-eager flip during this work.

## Revert

`git revert`; re-sync the runtime checkout. The lane then fail-closes again
(loudly, by design) — nothing else regresses.
