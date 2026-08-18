# 2026-08-18 — shadow_vol_window lane config (orch#1004 impl PR 1, s104 half)

STATUS:    delivered — one new lane config + one pin test; NO other config
           touched. Paired with the renquant-pipeline vol_window_license PR
           (cross-referenced in both PR bodies). NOTHING schedules this
           config: the daily-full lane wiring (readonly broker +
           `RENQUANT_READONLY_TAG=alpaca_shadow_vol_window`) is impl PR 2
           (orchestrator ops); deploys stay operator-gated.
WHAT:      `configs/strategy_config.shadow_vol_window.json` — the vol-window
           shadow lane profile: the CERTIFIED solo-xgb scorer + full prod
           funnel, `regime_admission` ENABLED (the refusal slot the license
           substitutes for), `vol_window_license` ENABLED with the frozen
           constants (threshold 0.135 STRICT, 20 trading days), the
           kill-switch env documented in the config itself. Plus
           `tests/test_strategy_configs.py::test_shadow_vol_window_lane_contract`
           pinning every load-bearing choice.
WHY/DIR:   orch#1004 approved design §7 impl PR 1 (verdict orch#1003, prereg
           orch#1001): the shadow lane that accrues the pre-committed
           activation evidence (≥20 ON-state sessions with positive realized
           h=60 top-decile spread) before any operator ask. Lane strategy
           profiles live in renquant-strategy-104.
EVIDENCE:  see §3 below (§4(b) keys).
NEXT:      impl PR 2 (orchestrator): daily-full Step for this lane (clone the
           Step-5 shadow-blend shape) + the AC3 readout. Operator-gated
           activation is design §4 Stage A — not this program of PRs.

## 1. Construction (every delta enumerated)

Base = the LAST solo-xgb PRODUCTION config (`0bd93d6~1:configs/
strategy_config.json` — the exact funnel the certified scorer served under:
kind=xgb on `artifacts/prod/panel-ltr.alpha158_fund.json`, global
calibration ON, adaptive mean+std buy floor, conviction gate, Kelly, QP),
then exactly these changes `[VERIFIED — exhaustive recursive diff run
2026-08-18; list is complete]`:

carried-forward post-blend prod changes (not blend deltas):
- `regime_params.BULL_CALM.max_position_pct` 0.12 → 0.30 and
  `ranking.kelly_sizing.max_concentration` 0.12 → 0.30 (e00d935, operator
  directive 2026-08-06 — applied to every live lane so shadow-vs-prod deltas
  stay a model comparison, not a sizing confound);
- `sleeve._comment` correction (f3f888a, docs-only).

lane deltas (each with an in-place `_shadow_vol_window_*` note):
- `ranking.panel_scoring.regime_admission.enabled` false → true;
- `ranking.panel_scoring.vol_window_license` ADDED: enabled=true,
  threshold=0.135, vol_window_days=20, `_comment` (frozen semantics,
  consumer, governance precedence, ledger, PR-2 readout) and `_kill_switch`
  (`RENQUANT_VOL_WINDOW_LICENSE_DISABLE`, design AC4);
- `ranking.panel_scoring.shadow_models` REMOVED (the clf/momentum shadow
  legs run on their own lanes; duplicating them here adds runtime and
  duplicate shadow rows for zero information);
- `wf_gate.diagnostic_only_buy_admission` REMOVED (EXPIRED 2026-08-15 and
  doubly inert — the served artifact stamps diagnostic_only=false; the
  validator fails closed on expiry — a dead operator authorization does not
  belong on a new reviewed surface; behavior identical either way);
- top-level `_shadow_vol_window_profile` provenance note.

## 2. The one deliberate interpretation, flagged for review

Design §3 says "top-decile (by served panel score)". Production TODAY serves
the z-blend (operator override 0bd93d6); the orch#1003 CERTIFICATION scored
the solo-xgb artifact `panel-ltr.alpha158_fund.json` with its params
verbatim (`[VERIFIED — orch#1003 §8 pins]`). This lane pins the CERTIFIED
scorer, not today's prod blend, because the activation evidence must count
the certified thing (the same correspondence logic design AC3 itself applies
to the horizon, citing orch#999). Consequence: the lane's model-relevant
config projection is IDENTICAL to prod's
(`sha256:f8fb2259b2bf1537` = the certified artifact + calibrator
fingerprint), so artifact consistency and the calibrator's
strict_scorer_match hold with no re-stamp `[VERIFIED — fingerprint_config
computed 2026-08-18 on both configs]`. If review prefers "served = whatever
prod serves", that is a one-key change (kind/components) — but it would
decouple the lane's evidence from the certification.

## 3. Evidence

(a) Conclusion: the lane config exists, is internally coherent with the
certified pins, arms exactly the refusal slot the license fills, and nothing
else in the repo changed.

(b)
- `artifact:` this PR's diff — one new config + one test + this doc; the
  consumer mechanism is the paired renquant-pipeline PR
  (`kernel/panel_pipeline/vol_window_license.py` via
  `RegimeModelAdmissionTask`).
- `prod or exp:` neither — a lane config NOTHING schedules yet (impl PR 2
  wires the daily-full lane; deploys operator-gated). `strategy_config.json`
  / golden / every other lane byte-untouched `[VERIFIED — git status shows
  only the three new/edited files]`.
- `existing data:` frozen constants and burden are prior work: orch#1001
  prereg §2 (0.135 STRICT, 20 td), orch#1003 §1/§8 (CONFIRMED; served
  artifact content 6461b827…, config fp sha256:f8fb2259b2bf1537), design
  orch#1004 §§2-5 (window semantics, shadow-first, ≥20 ON-session burden,
  kill-switch AC4).
- `best-known?:` honest scope — (i) the solo-xgb base is 0bd93d6~1 plus the
  two carried post-blend changes; the exhaustive diff in §1 is the complete
  delta set, so any drift the base had accumulated elsewhere is inherited
  by construction; (ii) the certified-scorer interpretation of "served
  panel score" (§2) is deliberate and review-flagged; (iii) the lane's
  never-submit posture is the runner's (readonly broker + lane tag), not a
  config bit — same as every existing shadow lane.
- `scope:` one new lane config + its pin test; no production config, no
  schedule, no deploy, no pin advance.

Suite: baseline 102 passed / 1 skipped `[VERIFIED — run 2026-08-18 at
origin/main f3f888a]`; after this PR 103 passed / 1 skipped (`make test`)
`[VERIFIED — run 2026-08-18]`.

## 4. Files

- `configs/strategy_config.shadow_vol_window.json` — new.
- `tests/test_strategy_configs.py` — new lane-contract pin test + the lane
  added to the required-configs parse list.
- `doc/progress/2026-08-18-shadow-vol-window-lane.md` — this doc.
