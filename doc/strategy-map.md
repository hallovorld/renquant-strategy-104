# Strategy map — what renquant-104 is optimizing, measured state, and the signal roster

STATUS: POINTER document (deliberately). Canonical sources live in renquant-orchestrator
(the control-panel repo) and the umbrella, and are linked per section; this file states
WHAT APPLIES TO THIS STRATEGY and where the living version is. Do NOT copy numbers,
dates, artifact identities, or roster states into here by hand — the
hand-maintained-snapshot rot of umbrella `doc/arch/strategy-104.md` (stale within weeks,
broke a design round) is the disease this format avoids. Every cross-repo pointer in this
doc is registered in `doc/strategy-map-pointers.json` and link-checked (§6).
DATE: 2026-07-02

## 1. The objective this strategy serves

```
Book = β(FLOOR: parking sleeve + ops discipline)
     + Active: IR = TC × IC_combined × √BR_eff
     + EXEC (entry/exit implementation gain) − LEAK (process failures)
```

Target G*: the Sharpe/alpha/drawdown/process bar. Its horizon, numeric levels, and
re-measurement cadence are owned by orchestrator
`doc/design/2026-07-02-unified-107-master-plan.md` (§0 state vector) and
`doc/research/2026-07-02-ic-ceiling-institutional-gap-107-route.md` (bounds, gates,
fallback ladder) — none of that is restated here, including the horizon date; it is
re-measured on its own cadence and this doc does not track that cadence.

## 2. Measured state (WHERE to read it, not a copy)

The weekly KPI scorecard (deployed fraction, floor gap vs SPY, gate-verdict age, ledger
coverage, PIT accrual, collector liveness, sign-laundered count, buy-side TC) is generated
by orchestrator `scripts/kpi_scorecard.py` into orchestrator
`doc/research/evidence/kpi_scorecards/` (one dated JSON per run). That JSON is the truth;
this doc intentionally carries no numbers.

## 3. The signal roster (what this strategy scores with, present and planned)

- **Live primary + shadow**: owned by the umbrella GENERATED production snapshot,
  `RenQuant/doc/arch/strategy-104-snapshot.md` — rendered from the pinned config and each
  artifact's own stamped metadata (CI-enforced fresh); it states the active/shadow scorer
  kind, artifact identity, and staleness as current facts. Dated promotion narrative (who
  flipped what, when, why) lives in `RenQuant/doc/arch/strategy-104.md`. Neither the
  scorer name nor any promotion date is restated here: a prior revision of this bullet
  hand-copied both and was already contradicted by the generated snapshot within the same
  review cycle — the exact drift this format exists to prevent.
- **Planned stack (pre-registered)**: orchestrator
  `doc/design/2026-07-02-m-sig-signal-stack-spec.md` (frozen r4) owns the candidate
  definitions, thresholds, deadlines, and per-candidate freeze status. What applies to
  this strategy, stated as contract only:
  C1 estimate-revision drift — INFORMATIVE-ONLY monitoring, EXCLUDED from the voting
  family (may never independently decide GO/KILL for the stack); its accrual is bounded
  to the same registry-wide gate date as every other candidate (spec §1.1/§3), not
  indefinite — the date itself lives in the spec, not here.
  C2 quality composite — the contract is genuine as-filed fundamentals: an observation is
  PIT-admissible ONLY through a real `acceptedDate`/`filingDate` availability timestamp;
  where the vendor payload lacks those fields, availability falls back to the SEC
  EDGAR-derived `available_date` join (base-data
  `src/renquant_base_data/sec_fundamentals.py`); an observation with neither is
  INADMISSIBLE — excluded from the cross-section, never proxy-backfilled. No vendor
  substrate is blessed as the signal input by this map; admissibility is proven per
  observation by the spec's rule (§1.2).
  C3 regime-conditioned residual momentum; C4 trend-scanning label.
  Thresholds are frozen in the spec; policy/threshold ADOPTION lands HERE (configs/) when
  a candidate clears its bar.
- **Closed (do not re-pitch)**: the settled-NULL roster is owned by the M-SIG spec (§2
  design rule 3, "no settled-NULL re-litigation") and the umbrella registry
  `RenQuant/doc/research/failed-experiments-log.md`. Not enumerated here — this map states
  the category and its owners; it does not maintain a second roster state machine.

## 4. Policy knobs THIS repo owns (the #210 ownership split)

`configs/strategy_config.json` (values live in the config, not restated here — see keys):
`mu_floor` (conviction floor; uncertainty-haircut design M3 pending), `panel_buy_top_n`
(A-2 widening deferred behind D1-or-M3), `qp_cash_drag_lambda` (A-1 confirmed a production
no-op mechanically — orchestrator #240), regime params (`BULL_CALM` cap, reserves),
`model_staleness_days`, wash-sale/anti-churn.
Sleeve policy (β-budgeted SPY/SGOV split formula) adopts here when S7 lands — decision
memo: orchestrator `doc/research/2026-07-02-rs1-parking-sleeve.md`.

## 5. Change protocol

Signal/policy changes reach this repo ONLY through: frozen prereg (orchestrator) →
measurement on the S5/S8 substrate → design PR here citing the evidence → config PR.
Direct config edits without that chain are the anti-pattern this map exists to prevent.

## 6. Pointer integrity (how this doc is kept from rotting)

Every cross-repo path named above is registered in `doc/strategy-map-pointers.json` — a
machine-readable manifest (repo / path / ownership, plus the owning repo's main commit
each pointer was last verified against, giving each pointer an immutable permalink form).
`tests/test_strategy_map_pointers.py` enforces, fully offline: (a) every backticked
cross-repo path in this doc's prose is represented in the manifest; (b) every pointer and
config key owned by THIS repo resolves locally; (c) in integration mode
(RENQUANT_POINTER_INTEGRATION=1, set only after the canonical sibling checkouts of
`RENQUANT_REPOS.md` are synced to their canonical state), every cross-repo pointer must
resolve inside its owning checkout — outside that mode the check skips loudly, because a
sibling working tree on an arbitrary branch is not canonical (merged-is-not-deployed).
No network calls in unit tests. The umbrella integration job consuming this manifest is
the standing re-validation path (wiring tracked in the progress doc).
