# rotation.enabled=false — the rotation engine is unvalidated churn (orch row 2e)

STATUS: production-config write, ONE key, merge gated on orchestrator
LONG-ledger row 2e (evidence-backed; first-hand operator confirmation slot
PENDING — the agent proceeds under the operator's 2026-08-30 max-benefit
directive with a single-key revert available at every step).

WHAT: `rotation.enabled` **true → false** in the active config, its golden
twin, and the six prod-mirror lanes (`shadow_blend`, `shadow_blend_momentum`,
`shadow_momentum`, `shadow_blend_momentum_fast`, `shadow_blend_rb_mom`,
`shadow_blend_rb_fast`) — the same mover set as rows 2a/2b/2d, forced by the
semantic-pin chain (`test_active_and_golden_semantic_config_match`,
`test_shadow_blend_profile_semantic_pins`, the fleet-delta assertions), which
was satisfied by moving the mirrored value, never by loosening a pin — plus
`rotation._enabled_reason` on active + golden. Every other `rotation.*` key
(`min_expected_advantage_pct` 0.06, `target_horizon_days` 60,
`min_rotation_hold_days` 7, `transaction_cost_pct` 0, `panel_buy_top_n` 3,
the whole `joint_actions` block) keeps its value, so a validated design
re-enables with a single-key flip. Frozen arms (`shadow`, `shadow_a`,
`shadow_b`, `shadow_vol_window`) keep `enabled: true` — their preregs froze
the arm definition and a mid-experiment edit would corrupt the readout.

WHY (§4b, all read-only, 2026-08-29/30):
- **Never validated.** The served recipe's WF gate metadata records
  **0 rotation trades in all 3 validated cuts** [VERIFIED —
  `metadata.wf_gate_metadata` on the served panel artifact, parity audit
  2026-08-30]; the gate never exercised the engine, so no WF number covers it.
- **The advantage estimate is a 5-day oscillator ×12.** `net_adv` compares
  per-ticker `expected_return` values that are a 5-day RSI/MACD/CCI/BBP/ADX
  model's calibrated ER scaled ×12 to the 60-day horizon; across live
  sessions **22% of session pairs jump ≥ the 0.06 threshold** and there are
  **17 sign flips in 12 names** [VERIFIED — `candidate_scores` vs
  per-ticker ER, logic forensics 2026-08-30]; `transaction_cost_pct=0` so
  nothing prices the round-trip.
- **Live cost.** Ledger forensics 07-17..08-28 (broker portfolio history +
  FIFO over fill activities): 33 round-trips realized **+$4.32** total,
  gross traded $60.1k = **5.55× turnover in 6 weeks**; the churn set
  (APH/CRWD/NET/NVDA/SPG/VLO) = **55.6% of gross traded $**; exit-reason
  P&L: rotation **8 trips +$64**; the two stop-loss trips (NET −150, DDOG −57
  = **−$207**) were both RE-ENTRIES within days of an exit [VERIFIED —
  ledger forensics 2026-08-30].
- The 08-29 root cause (entry dates re-seeded from the oldest-ever buy →
  `min_hold_days` bypassed) is being fixed in the umbrella separately; that
  fix removes one bypass, not the unvalidated advantage signal.

Authority: `strategy_config.json` is read-only under LONG-ledger row 2.
Row 2e (renquant-orchestrator, this batch) records the one-time authority:
basis = the operator's 2026-08-30 directive 「你问的6个问题基本都不是真正的问题!
你自己按照受益最大方向推进」 + the three evidence pointers above; the
change-specific first-hand confirmation slot is PENDING (operator may confirm
or veto). Expiry/restore: until a rotation design passes a WF gate.
Rollback: single-key revert PR + pin re-advance.

Deploy: normal ordered path — umbrella pin advance + runtime sync as
separate reviewed steps. Day-1 check: `daily_104` log shows no
`ROTATION_EXEC`/`ROTATION_SELECT` lines and the rotation task reports
disabled; exits (stop_loss, model_protection, model_sell) still fire.

§4b: full suite on CI-matching py3.10 — see PR body for the count
(base 104 passed / 1 skipped); new pin
`test_rotation_engine_is_disabled_until_validated`.
