# 2026-07-26 — shadow slot: top-decile classifier (blend clf leg)

STATUS:    planned
WHAT:      Documents the proposed `ranking.panel_scoring.shadow_models` addition
           (topdecile_clf_blend_leg, kind xgb, identity double-pinned via
           expected_content_sha256 + expected_config_fingerprint so the health
           record faults on any artifact swap). Codex review flagged the earlier
           head as a direct write to the protected production path
           `configs/strategy_config.json`; that write is REVERTED in this PR.
           The config change itself is deferred to the operator-authorized
           activation step (see NEXT), not made here.
WHY/DIR:   Piece 2/3 of pipeline#213's rollout: wiring the clf leg of the
           CONFIRMED blend objective (model#74/75/76, disjoint-seed +0.0687
           CI90[+0.0156,+0.1269]) into the shadow scoring surface so it can be
           observed alongside the prod scorer before the blend readout job
           (piece 3/3) and eventual activation. Advances the pipeline#213
           frozen-readout rollout; does not touch the live decision path.
EVIDENCE:
  artifact:      umbrella artifacts/shadow/panel-clf.top-decile.fwd60.json (additive,
                 produced by merged model#77 trainer; verified loading via the PINNED
                 runtime PanelScorer with valid probability smoke scores)
  prod or exp:   experiment/proposal only in this PR; no config file is modified
  existing data: pipeline#213 (MERGED) frozen readout governs; model#74/75/76 chain
  best-known?:   mirrors the existing shadow_models entry shape; kind=xgb reuses the
                 registered handler — zero new runtime code
  scope:         proposed shadow-slot entry, not yet applied; no production scorer
                 change; blend would be computed by the readout job offline
Proposed config (apply only at the operator-authorized activation step, appended to
`ranking.panel_scoring.shadow_models` in `configs/strategy_config.json`):
```json
{
  "name": "topdecile_clf_blend_leg",
  "kind": "xgb",
  "artifact_path": "artifacts/shadow/panel-clf.top-decile.fwd60.json",
  "expected_content_sha256": "99687a900bee01c472c327fb15d05d5da6a8f5e42f1e0856905cf32554e47b55",
  "expected_config_fingerprint": "sha256:1d8f167fed18cd8cb1e0760251fdd5398724e630462d92b41561d2e19973e41b",
  "_role_2026_07_26": "clf leg of the CONFIRMED blend objective (model#74/75/76, disjoint-seed confirmed +0.0687 CI90[+0.0156,+0.1269]); scores = P(top decile fwd_60d_excess); the blend z(prod)+z(clf) is computed OFFLINE by the readout job, never in the scorer; governed by pipeline#213's FROZEN forward readout (INFO@60, GATE@120 matured sessions); NOT a production scorer"
}
```
NEXT:      rollout piece 3/3 (orchestrator readout job + launchd, needs the grant);
           then the operator applies the proposed config block above as the
           separately authorized activation step.
