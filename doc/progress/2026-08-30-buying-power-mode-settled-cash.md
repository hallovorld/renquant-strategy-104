# execution.buying_power_mode=settled_cash — never size buys on unsettled proceeds or margin (orch row 2f)

STATUS: production-config write, ONE key, authorized by orchestrator
LONG-ledger row 2f (AUTHORIZATION COMPLETE 2026-08-30 12:09 PDT; row 2f
merged to orchestrator main as orch#1097).

WHAT: `execution.buying_power_mode` **`non_marginable_buying_power` →
`settled_cash`** in the active config, its golden twin, and the six
prod-mirror lanes (`shadow_blend`, `shadow_blend_momentum`, `shadow_momentum`,
`shadow_blend_momentum_fast`, `shadow_blend_rb_mom`, `shadow_blend_rb_fast`)
— the same mover set as rows 2a/2b/2d/2e, forced by the semantic-pin chain
(`test_active_and_golden_semantic_config_match`,
`test_shadow_blend_profile_semantic_pins`, the momentum/fast lane pins and
the fleet-delta assertions), which is satisfied by moving the mirrored value,
never by loosening a pin — plus `execution._buying_power_mode_reason` on
active + golden. Every other `execution.*` key (`enabled` true,
`t2_settlement_days` 1, `fractional_shares.enabled` false,
`software_stops.enabled` false) keeps its value. The 2026-05-24
`_settlement_reason_2026_05_24` note is kept as history; the new reason
records that it is superseded. Frozen arms (`shadow`, `shadow_a`, `shadow_b`,
`shadow_vol_window`) keep `non_marginable_buying_power` — their preregs froze
the arm definition and a mid-experiment edit would corrupt the readout.
The existing pin `test_execution_contract_is_explicit` is updated to the new
value; a new pin `test_buys_are_sized_on_settled_cash_never_margin` guards
the mover set, the untouched siblings, the reason and the frozen arms.

WHY (§4b, all read-only):
- **The live adapter never read this key.** Umbrella
  `live/alpaca_broker.py::get_cash` returned `non_marginable_buying_power`
  unconditionally (P0-9, 2026-05-20); the sim reads the key, live did not
  [VERIFIED — RenQuant#624 source audit of the order path: `daily_104.sh` →
  `daily-bridge` → umbrella `live/alpaca_broker.py` +
  `backtesting/renquant_104/adapters/runner.py`].
- **Ledger forensics 2026-08-30:** 08-27 HPE $1,034 bought with settled cash
  $33; 08-28 WELL $1,904 + NET bought with settled cash −$1,140 → account
  1.11× on margin at the 08-28 close (`account.cash` −$1,139.70)
  [VERIFIED — operator findings 2026-08-30 as recorded in RenQuant#624;
  not re-read from the broker here].
- **RenQuant#624** makes the adapter honour the key with the vocabulary
  `settled_cash | non_marginable_buying_power | buying_power` (default
  `settled_cash` when absent; a ≤ 0 balance sizes to $0 under the named
  reason `no_settled_cash`; same-bar unsettled sell proceeds are not
  credited under settled sizing) and logs `runner: buy-sizing cash=… nmbp=…
  mode=…` every run [VERIFIED — #624 diff, `live/broker.py` vocabulary;
  CI green at e0729f4]. Because #624 HONOURS the key, the live number stays
  nmbp after its deploy until this config says `settled_cash` — this PR is
  the second half of the fix.
- **Sim/live parity:** the sim reads the same key with the same canonical
  names, so declaring `settled_cash` here keeps both paths in ONE mode.

Authority: `strategy_config.json` is read-only under LONG-ledger row 2.
Row 2f (renquant-orchestrator#1097, MERGED) records the one-time authority:
first-hand, change-specific operator confirmation 2026-08-30 12:09 PDT —
agent prompt 「确认 row 2e:rotation.enabled=false;确认 row
2f:execution.buying_power_mode=settled_cash」, operator reply 「确认」.
Scope = this single key + its reason. Expiry/restore: **until the operator
authorizes margin use by a new row**. Rollback: single-key revert PR + pin
re-advance.

Ordering: RenQuant#624 must merge + live fast-forward FIRST or TOGETHER with
the pin advance carrying this change — with the old adapter the key is
ignored on live (sim would switch alone, breaking parity); with #624 live
and this config still nmbp the live number is unchanged.

Deploy: normal ordered path — umbrella pin advance + runtime sync as
separate reviewed steps. Day-1 check: the `daily_104` log carries
`runner: buy-sizing cash=… nmbp=… mode=settled_cash`; with `account.cash`
≤ 0 the run records `no_settled_cash` and places no BUY; sells untouched.

§4b: suite under the RenQuant venv (py3.10) — see PR body for the count
(base 102 passed / 1 skipped / 1 failed, the failure
`test_config_drift_cli_exposes_repo_root` pre-existing and environmental);
new pin `test_buys_are_sized_on_settled_cash_never_margin`.
