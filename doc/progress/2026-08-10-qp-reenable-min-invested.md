# qp deployment knobs re-enabled — the 2026-05-23 condition is met

STATUS:    in-progress — config change through review. MERGE-GATED by
           LONG row 2 (agent writes to configs/strategy_config.json
           are read-only-protected): row 2a's non-generalisation
           clause ("any other production-config write needs its own
           row") requires an operator-authorized LONG-ledger row for
           THIS write, and none exists yet [VERIFIED — git show
           origin/main:doc/memory/long-term-agreements.md ends at row
           10, checked 2026-08-10]. Deployment to the running machine
           is a further SEPARATE, operator-granted pin-sync step.

WHAT:      qp_min_invested_pct 0 -> 0.7 and qp_cash_drag_lambda
           0 -> 0.05 across all 11 strategy_config profiles (active,
           golden, and the 9 shadow profiles — the semantic-pin tests
           enforce shadow==active on this section, and the deployment
           posture is a funnel-wide property, not a shadow delta). The
           _qp_min_invested_edge_reason string now records the MET
           condition with citations; the positive-edge guard
           (qp_min_invested_requires_positive_edge: true, edge floor
           0.002) is UNCHANGED.

WHY/DIR:   The 2026-05-23 recorded condition ("re-enable only after WF
           shows benchmark-relative alpha survives the strict
           admission gate") is MET by the orch#955-frozen prereg's
           official PASS (orch#957: 898/1,357 realized days vs floor
           700; +0.0981 sigma/day vs bar 0.0658; bootstrap CI
           [+0.0139, +0.1782] excludes 0). Value provenance — no
           invention: 0.7 restores the 2026-05-05 designed soft floor
           (umbrella commit 6fa4700, pre-dating the 05-23 disable);
           0.05 is qp_solver's own documented moderate default. The
           two knobs form one mechanism (penalty = lambda * max(0,
           target - sum w)); flipping either alone is inert, which is
           why both move together.

EVIDENCE:  artifact:      the 11 config diffs in this PR
           prod or exp:   config-through-review; NOT deployed by this
                          PR (merged != live; pin sync is operator-
                          granted)
           existing data: orch#957 verdict note + its verbatim runner
                          outputs; orch#945 knob sweep (lambda inert at
                          target=0; turnover cap 0.15 paces deployment
                          ~0.706 — built-in gradualism); qp_solver
                          docstring (soft-target contract, tuning
                          table)
           best-known?:   yes — what PASS does not license is stated in
                          the verdict note s3 (gross/selection-level/
                          pre-sizing; no gate change; no auto-deploy)
           scope:         11 JSON profiles, 3 lines each (2 values + 1
                          reason string); no code

TESTS:     make test (RenQuant venv): 102 passed, 1 skipped — includes
           the shadow semantic-pin tests that enforce profile
           consistency on exactly this section.

NEXT:      (1) Codex code-owner review of this diff; (2) operator
           decision transcribed as a LONG-ledger row (SOP-L; the
           strategy-104#94 -> orch#883 -> row-2a protocol) authorizing
           this two-knob write — the agent may not author that row on
           its own judgment, and the 2026-05-23 re-enable condition
           was Codex-authored, so no operator decision is on record
           yet; the basis offered for that row is the in-config
           2026-05-23 recorded condition + prereg section 6 (orch#955:
           the PASS deliverable is this PR "THROUGH REVIEW") + the
           orch#957 official PASS; (3) merge; (4) operator-granted pin
           sync on the running machine; (5) first post-enable sessions
           watched via the L1 exposure shadow + funnel receipts (the
           deployment pace is bounded by the 0.15 turnover cap;
           expected staircase, not a jump).
