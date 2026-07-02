# Strategy map pointer doc — docs PR

STATUS:   docs only.
WHAT:     `doc/strategy-map.md` — the strategy-facing map (objective equation + where the
          measured state lives + signal roster present/planned/closed + the policy knobs
          this repo owns + the change protocol). POINTER format by design: canonical
          numbers/specs live in orchestrator and are linked, never hand-copied — the
          umbrella strategy-104.md hand-snapshot rot is the counterexample this avoids.
WHY:      operator (2026-07-02): the strategy repo should carry its own map. Per the #210
          ownership split it should — policy is this repo's; the map states what applies
          here and where the living truth is.
NEXT:     review; the M9 generated-snapshot work (orchestrator A6 follow-up) will link back
          to this map.

## Round 2 (Codex review: stale pointer + hand-copied literals)

**Finding.** The doc's own C2 description ("FMP annual") was already stale against
orchestrator #243's r4-frozen final design (C2 requires a genuine `acceptedDate`/
`filingDate` availability timestamp — SEC EDGAR `available_date` when FMP lacks one;
otherwise INADMISSIBLE, never proxy-backfilled). C1's status didn't reflect #243's final
verdict either (INFORMATIVE-ONLY, excluded from the C2/C3/C4 voting family, bounded to the
same 2027-Q4 deadline, not indefinite accrual). Separately, despite the doc's own "do not
hand-copy numbers" charter, §1 restated G*'s numeric bar (Sharpe/alpha/DD) and §4 restated
live `strategy_config.json` values (`mu_floor 0.03`, `panel_buy_top_n 3`,
`qp_cash_drag_lambda 0`, `BULL_CALM cap 0.12`) — exactly the values that will drift the
moment the owning file changes without this doc being updated in lockstep.

**Fix.**
- C2 rewritten to name the actual admissibility rule and its SEC-EDGAR fallback mechanism
  instead of "FMP annual."
- C1 rewritten to INFORMATIVE-ONLY / excluded-from-voting, matching #243's frozen r4 text.
- G* (§1) and the `configs/strategy_config.json` knobs (§4) no longer restate numeric
  values — both now name the owning config key / canonical doc section only.
- New `tests/test_strategy_map_pointers.py` (4 tests): every config key §4 claims this repo
  owns is asserted to genuinely resolve inside `configs/strategy_config.json` (dotted-path
  lookup, fails loudly if a key is renamed/removed); the doc is asserted to still name each
  claimed key by leaf name (keeps the test fixture honest against the prose, not an
  independently-invented list); a regression guard against the exact hand-copied-value
  pattern this round found (`mu_floor 0.03`, `panel_buy_top_n\` (3;` no longer appear
  verbatim next to their key names).

**Evidence:** 4/4 new tests pass; existing `test_config_drift.py`/`test_strategy_configs.py`
suites pass (29/30 — the one pre-existing failure, `test_config_drift_cli_exposes_repo_root`,
reproduces identically on `origin/docs/strategy-map` before this round's changes too — a
package-installation/subprocess-invocation issue in an ad-hoc worktree, not caused by or
related to this fix).
