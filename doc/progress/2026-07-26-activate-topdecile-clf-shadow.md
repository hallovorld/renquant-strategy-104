# 2026-07-26 — ACTIVATION: topdecile clf shadow slot (operator-authorized)

STATUS:    executing the separately authorized activation step from #63
WHAT:      applies the exact config block preserved verbatim in the merged #63
           progress doc: shadow_models += topdecile_clf_blend_leg (identity
           double-pinned).
WHY/DIR:   #63 review (correctly) refused a latent write to the protected config
           and deferred to operator-authorized activation. That authorization is
           now ON RECORD (operator, session 2026-07-26: '激活批次预授权' and
           '我想让他现在就上线开始陪跑'); this PR is the authorized step.
EVIDENCE:
  artifact:      umbrella artifacts/shadow/panel-clf.top-decile.fwd60.json
                 (sha256 99687a90…, matches expected_content_sha256; verified
                 loading via the PINNED runtime PanelScorer, valid probabilities)
  prod or exp:   PROD config change under explicit operator grant; shadow-only
                 consumer (ApplyShadowScoringTask); primary scorer untouched
  existing data: pipeline#213 (MERGED) frozen readout governs; model#74/75/76
  best-known?:   block identical to the #63-preserved proposal, plus the grant
                 citation field
  scope:         first scoring session = next NYSE day 13:55 PT; readout job
                 (piece 3/3) lands separately this week — sessions accrue
                 regardless via MLflow + the #211 health record
REVERT:    remove the entry (single list item) + pin re-advance; or
           promote_pin.py revert --apply to the prior strategy pin
NEXT:      merge -> pin advance (already-granted batch) -> verify tomorrow's
           health record shows topdecile_clf_blend_leg loaded+scored.
