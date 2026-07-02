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
- New `tests/test_strategy_map_pointers.py` (4 tests) covering LOCAL config-key pointers
  only: every config key §4 claims this repo owns is asserted to genuinely resolve inside
  `configs/strategy_config.json` (dotted-path lookup, fails loudly if a key is
  renamed/removed); the doc is asserted to still name each claimed key by leaf name; a
  regression guard against the exact hand-copied-value pattern this round found.
  [CORRECTED in round 3: this round's test file docstring called itself a check of
  "cross-repo/config pointers" — it checked NO cross-repo pointer; that claim was false
  and round 3 replaces it with a real manifest-backed check.]

**Evidence:** 4/4 new tests pass; existing `test_config_drift.py`/`test_strategy_configs.py`
suites pass (29/30 — the one pre-existing failure, `test_config_drift_cli_exposes_repo_root`,
reproduces identically on `origin/docs/strategy-map` before this round's changes too — a
package-installation/subprocess-invocation issue in an ad-hoc worktree, not caused by or
related to this fix).

## Round 3 (Codex review: current-state facts still hand-copied; test overclaimed)

**Findings (all accepted).**
1. The "Live primary" bullet hand-copied the scorer kind, artifact identity, the operator
   date, missing-WF status, and the shadow scorer — current-state facts owned by the
   umbrella GENERATED snapshot. It was not only drift-prone: it was ALREADY contradicted
   by `RenQuant/doc/arch/strategy-104-snapshot.md` on main (the pinned-config snapshot
   states a different active/shadow pair than the bullet claimed).
2. C2 still led with the vendor substrate ("FMP-full fundamentals"), which is materially
   misleading post-PIT-review — historical FMP values are not proven as-filed by a date
   join alone.
3. The C1 deadline literal and the enumerated closed-signal roster were cross-repo status
   facts duplicated here (a second roster state machine).
4. `tests/test_strategy_map_pointers.py`'s name/docstring claimed a cross-repo link check
   while validating only five local config paths.
5. The progress record implied cross-repo pointer coverage that did not exist.

**Fix.**
- §3 live bullet is now a pure pointer: generated snapshot
  (`RenQuant/doc/arch/strategy-104-snapshot.md`) for current facts, narrative page
  (`RenQuant/doc/arch/strategy-104.md`) for promotion history; no scorer name, no artifact
  id, no dates restated.
- C2 rewritten contract-first: genuine as-filed fundamentals, PIT-admissible only via a
  real `acceptedDate`/`filingDate` availability timestamp; SEC EDGAR-derived
  `available_date` join (base-data `src/renquant_base_data/sec_fundamentals.py`) as the
  fallback availability source; neither present = INADMISSIBLE, never proxy-backfilled.
  No vendor substrate is blessed by this map.
- C1 deadline literal removed (points at the spec's registry-wide gate date); the closed
  roster is no longer enumerated — pointed at M-SIG §2 rule 3 and umbrella
  `doc/research/failed-experiments-log.md`.
- New machine-readable manifest `doc/strategy-map-pointers.json` (repo/path/ownership per
  pointer + the owning repo's main SHA at verification, i.e. an immutable permalink
  anchor per pointer). Test suite rewritten (8 tests, offline): every backticked
  cross-repo path in the prose must be registered in the manifest; this repo's own
  pointers/keys must resolve locally; in integration mode
  (RENQUANT_POINTER_INTEGRATION=1) every cross-repo pointer must resolve inside its
  owning sibling checkout, with a missing checkout a hard failure — outside that mode the
  check skips loudly (never fake-passes); no network anywhere.
- Why the integration assertion is env-gated rather than auto-engaging on directory
  presence: measured on this machine today, the sibling checkouts lag origin/main (the
  orchestrator working tree is on a feature branch without the 07-02 docs; the umbrella
  working tree does not yet have the generated snapshot) — merged-is-not-deployed. An
  auto-engaged check would therefore fail for reasons that are not pointer rot. The
  integration job syncs to canonical state first, then sets the flag.
- Every pointer in the manifest was re-verified against origin/main of its owning repo at
  the SHAs recorded in the manifest before this push (including the KPI scorecard output
  directory and the base-data module path).

**Deferred (explicit).** Wiring the umbrella integration job to consume
`doc/strategy-map-pointers.json` (sync canonical checkouts → run this suite with
RENQUANT_POINTER_INTEGRATION=1) is follow-up work in the umbrella repo (same slot as the
M9/A6 generated-snapshot linkage); the manifest is shaped for that consumer. Until then,
cross-repo existence is guaranteed at the recorded main SHAs (verified this round) and
re-checkable on any synced box via the flag.
