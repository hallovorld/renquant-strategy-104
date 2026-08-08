# Fast-lane genesis pin — both F2 components, marker retired

STATUS:    delivered. The two fast-lane blend components carry
           `expected_config_fingerprint`; the pending marker is gone. Both
           changes are in ONE commit because the marker demanded exactly that.

WHAT:      `configs/strategy_config.shadow_blend_momentum_fast.json`
             `/ranking/panel_scoring/components[1]`
           `configs/strategy_config.shadow_blend_rb_fast.json`
             `/ranking/panel_scoring/components[2]`
           both gain
             "expected_config_fingerprint": "momentum-v1_fast-2839b6c21db8ce13"
           and both lose `_2026_08_04_pending_first_artifact`.

WHY/DIR:   The marker's own terms: "At genesis, the SAME change must: add
           expected_config_fingerprint (measured from the published artifact
           params, momentum-v1_fast-<sha16>) and delete this marker — the #793
           consumer-checklist pattern applied at birth." Genesis has happened,
           so the marker is now a false statement about the lane's state and
           leaving it would be the exact half-done condition it was written to
           prevent.

EVIDENCE:  artifact:      RenQuant/backtesting/renquant_104/artifacts/
                          momentum_fast/momentum_artifact_ledger.jsonl (2 rows)
                          + the published artifacts at 2026-08-06/ and
                          2026-08-07/ momentum_residual_v0.json
           prod or exp:   prod — the live ledger and the artifacts the blend
                          loader reads
           existing data: the component carried NO identity pin at all; the
                          loader fail-closed on an absent component, which was
                          the designed dormant state, not a defect
           best-known?:   yes — first pin on this lane. The fingerprint was
                          RECOMPUTED from the published artifact params, never
                          copied from a prior note.
           scope:         two shadow-blend configs in renquant-strategy-104. No
                          code, no prod scorer, no pin advance elsewhere.

           ledger, read back:
             row 0  cutoff 2026-08-06  content e2358e83b5de…  prev_row_sha None
             row 1  cutoff 2026-08-07  content a4c6df6e240d…  prev_row_sha 7ffa32f3…
           recomputed via renquant_pipeline.momentum_identity.params_fingerprint
           (recipe: momentum-<params_version>-<sha256(canonical params)[:16]>):
             2026-08-06 artifact -> momentum-v1_fast-2839b6c21db8ce13
             2026-08-07 artifact -> momentum-v1_fast-2839b6c21db8ce13
           Both rows recompute to the SAME value, which is the point: the
           fingerprint derives from `params` and is INVARIANT across appends.

WHY NOT ALSO expected_content_sha256:
           The ledger is append-only and its whole-file digest changes on EVERY
           append. Pinning the content sha would fail-close the lane on every
           weekly run. The config fingerprint is the only identity that is
           stable across appends and still catches a training-config change,
           which is what this pin is for.

TWO CORRECTIONS TO THE MARKER'S OWN PREMISE:
        1. Genesis landed 2026-08-06 (ledger row 0), not "the first Saturday
           fast-lane run (2026-08-08)" the marker predicted. Today IS 08-08 and
           no 2026-08-08 artifact directory exists yet.
        2. The genesis artifact does NOT stamp `config_fingerprint` (the field
           is absent); the 08-07 artifact does. That field arrived with
           renquant-model#204. The pin is unaffected because the fingerprint is
           RECOMPUTED from params rather than read from the stamp — but a reader
           who trusted the stamp would have found nothing on the genesis row.

TESTS:     both configs re-parsed as JSON after the edit and the component was
           re-read to confirm the fingerprint is present and the marker is
           absent. No behavioural test exists for this lane yet — the blend
           loader's fail-close path is exercised only in the daily run.

NEXT:      Re-measure the mom_fast vs rb_fast score correlation (last measured
           rho = 1.0000, which is why the fast fleet was suspected of carrying
           less information than its lane count suggests) now that both lanes
           have a published artifact to score from.
