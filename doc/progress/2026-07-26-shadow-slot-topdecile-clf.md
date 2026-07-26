# 2026-07-26 — shadow slot: top-decile classifier (blend clf leg)

STATUS:    additive config entry; deploys only via the normal pinned-config sync
WHAT:      ranking.panel_scoring.shadow_models += topdecile_clf_blend_leg (kind xgb,
           identity double-pinned: expected_content_sha256 + expected_config_fingerprint
           so the health record faults on any artifact swap).
EVIDENCE:
  artifact:      umbrella artifacts/shadow/panel-clf.top-decile.fwd60.json (additive,
                 produced by merged model#77 trainer; verified loading via the PINNED
                 runtime PanelScorer with valid probability smoke scores)
  prod or exp:   config-owner PR; live unaffected until config sync (operator grant
                 at activation, together with the readout-job launchd step)
  existing data: pipeline#213 (MERGED) frozen readout governs; model#74/75/76 chain
  best-known?:   mirrors the existing shadow_models entry shape; kind=xgb reuses the
                 registered handler — zero new runtime code
  scope:         shadow-only; no production scorer change; blend computed by the
                 readout job offline
NEXT:      rollout piece 3/3 (orchestrator readout job + launchd, needs the grant);
           then activation.
