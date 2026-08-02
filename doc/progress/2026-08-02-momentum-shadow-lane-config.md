# Momentum shadow lane — the slice-4 s104 `shadow_models` entry (rides the slice-5 grant batch)

STATUS: planned (prepared and reviewed in advance; MERGES ONLY as step (d) of
the orch#757 one-grant deployment batch, per the model#197 build-order
amendment. Until that batch this PR carries a DO-NOT-MERGE banner and the
momentum lane stays deliberately dark).
WHAT: `momentum_residual_v0_shadow` added to
`ranking.panel_scoring.shadow_models` in BOTH `configs/strategy_config.json`
and `configs/strategy_config.golden.json` (identical entries — parity
asserted `[VERIFIED — json equality check, this session]`): config kind
`momentum_residual`, artifact_path
`artifacts/momentum/momentum_artifact_ledger.jsonl`, plus two narrative keys
(`_2026_08_02_momentum_shadow_lane` citing design model#195 + amendment
model#197 + orch#757 and the data-collection/no-verdict standing rule;
`_2026_08_02_pending_first_artifact` stating the resolution reality).
`tests/test_strategy_configs.py`: the exact shadow_models pin updated to the
two-lane state; a bounded `PENDING_FIRST_ARTIFACT` guard set + 2 new tests
(the guard names exactly this entry; the entry pins the ledger path with no
`..` escape).

WHY the ledger, not the dated artifact (the artifact_path decision):
- The #757 wrapper's job publishes each weekly artifact to
  `artifacts/momentum/<cutoff>/momentum_residual_v0.json` under the strategy
  serving root PLUS the append-only digest-chained ledger at
  `artifacts/momentum/momentum_artifact_ledger.jsonl` `[VERIFIED — orch
  origin/main ops/renquant104/momentum_train_weekly.sh OUT_ROOT +
  model origin/main tools/momentum_train_run.py LEDGER_BASENAME, read
  2026-08-02]`.
- Resolver base convention mirrored from the surviving blend leg: relative
  refs resolve strategy_dir-first, strategy_dir =
  `/Users/renhao/git/github/RenQuant/backtesting/renquant_104` `[VERIFIED —
  renquant-pipeline kernel/artifact_resolver.py `_candidates` (absolute →
  strategy_dir → repo_root) + orch#757 progress doc's serving-root ground
  truth]`. No `..`, no absolute path (the config-artifact-path-gate incident
  class).
- The `<cutoff>` component changes every week and the FIRST cutoff (= the
  first post-grant Saturday firing date) is unknowable in a PR that must be
  frozen under review and merged untouched inside the batch. The ledger is
  the ONE cutoff-stable file in the publish set: it exists from the first run
  onward, every weekly run appends to it, and its per-row
  `artifact_content_sha256` digest chain transitively pins every dated
  artifact beside it `[VERIFIED — model origin/main
  src/renquant_model_momentum/ledger.py `_ROW_REQUIRED` + chain checks]`.
  A dated-path pin would go stale within 7 days and demand a weekly config PR
  cadence nobody designed. Serving-handler contract declared in the narrative
  key: read the verified ledger tail row, load the dated artifact it names,
  verify its self-carried content_sha256.

RESOLUTION REALITY (why this PR merges only in the batch): until the slice-5
batch installs the job and it publishes the first artifact + ledger, the
configured path resolves NOWHERE — exactly the state model#197's ordering
exists to prevent from ever being deployed. No test in this repo resolves the
path against the operator's disk (that would be red or vacuously green per
machine — the tests-measure-the-operator's-disk failure class); the static
resolve gate is umbrella CI at pin-advance time. The bounded guard
(`PENDING_FIRST_ARTIFACT`, the launchd-manifest PENDING_INSTALL idiom) names
exactly this entry and the post-batch follow-up must delete the pending key
and shrink the set together.

## Slotting into the orch#757 grant checklist (order per model#197)

(a) preconditions → (b) install plist → (c) FIRST ARTIFACT published →
(d) **MERGE THIS PR** → (e) s104 pin advance + run-checkout sync.
Revert for (d): `git revert` of the merge (the checklist's own wording).

## Findings the batch must clear BEFORE step (e) — discovered this session, not solved here

- F-1 (pipeline): kind `momentum_residual` is NOT registered in the pipeline
  model registry `[VERIFIED — grep of renquant-pipeline origin/main
  model_registry.py: xgb/patchtst/hf_patchtst/regime_router/blend only,
  2026-08-02]`. After (e), ApplyShadowScoringTask would emit a daily
  load-fault health record for this lane (soft-fail; primary unaffected)
  until the pipeline-side handler slice + its pin land. Sequence that slice
  before or with (e), or accept the fault as the designed reminder.
- F-2 (umbrella gate, identity layer): the config-artifact-path gate requires
  every shadow entry's resolved artifact to carry `trained_date` +
  `config_fingerprint` inline metadata and fails closed otherwise
  `[VERIFIED — RenQuant scripts/check_config_artifact_paths.py
  `_metadata_identity` + `_check_one`, read 2026-08-02]`. The momentum
  artifact carries NEITHER (it has `trained_at_utc` / `cutoff_date` /
  `content_sha256` `[VERIFIED — model origin/main train.py artifact dict]`),
  and the ledger is JSONL (no loadable inline JSON metadata). Step (e) fails
  this gate for the momentum entry REGARDLESS of which publish-set file the
  config points at, until the umbrella gate learns a momentum-aware metadata
  rule (or the artifact contract adds those fields AND a dated-path pin
  becomes viable — it does not, per the cutoff argument above). Owner:
  umbrella gate extension; out of this repo's write scope.
- F-3 (umbrella gate, CI topology): the gate's verify-pinned-paths job
  resolves against the COMMITTED umbrella tree (`--data-root .` in CI); the
  blend-leg artifact passes because it is git-tracked
  `[VERIFIED — git ls-files backtesting/renquant_104/artifacts/shadow/]`.
  The momentum publish set is job-written machine state that nothing commits;
  the batch design must either commit the first publish set to the umbrella
  at (e) (operator action) or scope the gate's resolution for this lane.

EVIDENCE:
  artifact:      configs/strategy_config.json +
                 configs/strategy_config.golden.json (one entry each,
                 byte-identical; parity asserted) +
                 tests/test_strategy_configs.py (exact pin updated; +2 tests)
  prod or exp:   prod-adjacent but merge-inert BY ORDERING — nothing reads
                 this entry until the batch's pin advance (e); and this PR
                 does not merge until (d). No launchd job, config, artifact,
                 or state file on the machine is touched by this change.
  existing data: suite BEFORE this change: 93 passed / 1 failed / 1 skipped;
                 AFTER: 95 passed / 1 failed / 1 skipped `[VERIFIED — make
                 test in the worktree, this session]`. The 1 failure
                 (test_config_drift_cli_exposes_repo_root) is PRE-EXISTING
                 and environmental — it spawns `sys.executable` (system
                 python3.9) which lacks renquant-common; it fails identically
                 on the untouched main checkout `[VERIFIED — make test there,
                 this session]`. Zero new failures; both new tests pass.
  best-known?:   yes — mirrors the two standing precedents exactly: the
                 blend-leg entry's resolver-base convention (strategy_dir-
                 relative, no `..`) and the PENDING_INSTALL bounded-state
                 idiom for declared-but-not-yet-real surfaces.
  scope:         2 config files (one shadow_models entry each) + 1 test file
                 + this doc. No src/ change; no production input touched; no
                 manifest change (the xgb_prod_artifact_manifest is the xgb
                 promotion audit record and does not list the blend-leg lane
                 either).

NEXT: (1) review here (Codex), then FREEZE — revisions ride a superseding PR;
(2) the batch executes (a)→(e) with this PR as (d); (3) post-batch follow-up
PR deletes `_2026_08_02_pending_first_artifact` + shrinks
`PENDING_FIRST_ARTIFACT` (the relaxation cannot outlive the state it names);
(4) F-1/F-2/F-3 tracked on the orchestrator side as pre-(e) checklist items.

AC6 gate-design rule: N/A — shadow-only data collection; no capital-admission
gate is added or tightened; the primary scorer, calibrator, gates and sizing
are untouched.
