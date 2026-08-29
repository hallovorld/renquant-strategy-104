# Correlation guard reads the MAINTAINED artifact — `regime.correlation_artifact` path fix (orch#1065)

STATUS: PREPARED, NOT MERGEABLE YET. This is a production-config write
(orch LONG-ledger row 2) and merges only after (1) orch LONG-ledger **row 2d**
lands on orchestrator `main` with the operator's FIRST-HAND, change-specific
confirmation quoted verbatim, and (2) that confirmation is posted with
timestamp on this PR. Preparation was done without waiting because of the
operator's blanket directive of 2026-08-28 (Claude operator session, verbatim
「全面推进,不要停,别等我」 — "push everything forward, don't stop, don't wait
for me"); that directive is NOT cited as authority for the write — the
row-2a/2b precedent requires first-hand authority naming this change.

## Bottom line

`regime.correlation_artifact`: `"prod/watchlist-correlation.json"` →
`"watchlist-correlation.json"` in the eight carriers rows 2a/2b move (active,
golden, six prod-mirror lanes), plus `regime._correlation_artifact_reason` on
active + golden. Frozen arms untouched. Tests 104 passed / 1 skipped
(baseline 103 / 1; +1 pin test) [VERIFIED — `PYTHONPATH=src pytest -q tests/`].

## Evidence (all [VERIFIED] this session unless tagged)

- Served copy `artifacts/prod/watchlist-correlation.json`: mtime 2026-05-23,
  `as_of_date=2026-05-22`, window 2026-02-27..2026-05-22, `lookback_days=60`,
  `n_tickers=142` [VERIFIED — read-only json load on the live umbrella].
- Maintained copy `artifacts/watchlist-correlation.json`: mtime 2026-08-23,
  `as_of_date=2026-08-21`, window 2026-03-03..2026-08-21, 142 tickers, the
  same ticker set, symmetric, unit diagonal, no NaN, values rounded to 4dp
  [VERIFIED — same read]. Writer = pipeline `CorrelationJob`
  (`kernel/pipeline/pp_training.py:653-701`, rolling `tail(120)` window,
  writes `<strategy_dir>/artifacts/watchlist-correlation.json`).
- Both artifacts are `schema_version: 2` with the parser's contract keys
  (`matrix`, `as_of_date`, `data_window_start/end`); the prod copy's extra
  `lookback_days`/`n_tickers` are read by no consumer
  (`parse_correlation_artifact` reads only `matrix` + `as_of_date`,
  `kernel/walk_forward/correlation_guard.py:34-55`).
- Resolution — every consumer joins `<strategy_dir>/artifacts/<value>`:
  pipeline `kernel/preflight.py:1131-1137` (`_correlation_artifact_path`),
  `kernel/portfolio_qp/tasks.py:314-319`, umbrella
  `backtesting/renquant_104/adapters/runner_artifacts.py:36` (daily
  RunnerAdapter), LEAN `main.py:257-259` via `kernel/config.py:24-35`
  (`artifact_path` strips a leading `artifacts/`). Hence the bare filename.
- Contract run against the maintained file (read-only, pinned pipeline
  76ab129 which includes pipeline#299): `parse_correlation_artifact` → 142
  tickers, as_of 2026-08-21; `assert_correlation_no_leakage` no-op in live
  mode, passes for backtest_start ≥ as_of, raises for backtest_start
  2026-01-02 as designed; P-CORR-METADATA hard ok; P-CORR-FRESHNESS soft ok
  at 5 NYSE sessions (bound 30). Against the prod copy P-CORR-FRESHNESS is
  soft FAIL at 67 NYSE sessions — the alarm this PR silences by fixing the
  path, not by editing the bound.
- Measured cost of the divergence [VERIFIED — prior work, orch#1065 body]:
  80 dead blocks + 108 invisible conflicts at the 0.70 guard threshold.
- WF gate is inert to this key: `wf_config_builder.py:456-466` preserves the
  sim base's `regime.correlation_artifact` (renquant-backtesting main).

## Estimand note (flagged, not hidden)

The maintained writer's window is a rolling 120 bars (rounded 4dp); the
retired prod copy was a 60-day hand-build. Pairs ≥ 0.70: prod 171 vs
maintained 128 [VERIFIED — offline count over the two files]. The issue's
80/108 numbers were measured against a 60-day recompute; this PR
reconciles the reader to the writer that actually runs weekly, it does not
change the writer's window. If a 60-day estimand is wanted, that is a
pipeline change with its own evidence.

## Scope (exhaustive)

One key, eight files, one `_reason` key on two of them, one test. No other
key; `regime.correlation_guard_threshold` stays 0.7;
`correlation_artifact_max_age_sessions` is not introduced (pipeline default
30 applies). Frozen arms: `shadow`/`shadow_a`/`shadow_b` stay on
`sim/watchlist-correlation.json`; `shadow_vol_window` stays on
`prod/watchlist-correlation.json`.

## Deployment / rollback

Normal ordered umbrella pin advance + `-run` sync as separate reviewed steps.
Rollback = single-key revert PR + pin advance. Day-1 check: P-CORR-FRESHNESS
in the daily preflight reports `as_of_date` ≥ 2026-08-21 and age ≤ 30.
