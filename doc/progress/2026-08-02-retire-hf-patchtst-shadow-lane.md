# Retire the served hf_patchtst shadow lane (orch#741)

**Date:** 2026-08-02 · `renquant-strategy-104` · executes the config half of
renquant-orchestrator#741's RETIRE decision

## Bottom line

The served `hf_patchtst_pt07_strict_seed44_previous_primary` shadow lane is removed
from `ranking.panel_scoring.shadow_models` in **both** `configs/strategy_config.json`
and `configs/strategy_config.golden.json`, and the `readonly_shadow` entry is removed
from `configs/xgb_prod_artifact_manifest.json`. A `_2026_08_02_patchtst_retirement`
narrative key is added beside the existing history keys in all three files. **This PR
is shadow-only and merge-inert: no live surface changes until the operator's separate
deployment grant (checklist in the companion orchestrator PR's progress doc).**

## Why (the decision, not re-argued here)

Decision recorded on renquant-orchestrator#741 (2026-08-02 decision comment, under the
operator's standing delegation of research-line decisions):

- **Governance:** served artifact **625 days** stale vs the **28-day** RFC #210 SLA
  (~22x) `[VERIFIED — orch#741 decision comment, measurement provenance orch#731]`;
  its refresh/promotion chain has **never once completed** (22/22 trigger-fired chain
  FAILEDs, 36 non-acting wf-promote runs)
  `[VERIFIED — orch#741 decision comment, measurement provenance orch#724]`.
- **Merit:** the lane's own frozen preregistered evaluation (model#90, `control_ok:
  true`) scored the PatchTST arm **PERSISTENCE-DRIVEN** while both comparison arms
  scored FRESH-INFORMATIVE on the same machinery
  `[VERIFIED — orch#741 body quoting renquant-model
  doc/research/data/2026-07-29-clf-wf-closure-bundle/artifacts/corrected-eval/verdict.json]`.

**Explicitly preserved:** PatchTST-the-architecture. This retires the SERVED
625-day-stale artifact and its dead refresh chain; any future PatchTST proposal enters
as a fresh candidate through the gate.

## What changed `[VERIFIED — this session, git diff]`

| file | change |
|---|---|
| `configs/strategy_config.json` | `shadow_models[name=hf_patchtst_pt07_strict_seed44_previous_primary]` removed (matched by name, not index); `_2026_08_02_patchtst_retirement` key added beside `_2026_06_23_xgb_promotion` |
| `configs/strategy_config.golden.json` | identical edit; prod/golden byte-consistent in the edited region |
| `configs/xgb_prod_artifact_manifest.json` | `readonly_shadow` block (a CURRENT-state listing of the lane, not a historical note) removed and replaced by the retirement narrative key; this executes the manifest's own third `follow_up_exit_criteria` item ("retire it from shadow") |
| `tests/test_strategy_configs.py` | pins the RETIRED state: lane name absent from `shadow_models` in both configs, retirement key present and identical in both, `readonly_shadow` absent from the manifest; `topdecile_clf_blend_leg` remains the only shadow model |

## Shadow-only proof

- Primary scoring path untouched: `panel_scoring.kind == "xgb"`,
  `artifact_path == "artifacts/prod/panel-ltr.alpha158_fund.json"`, calibrator,
  conviction gate, regime params, kelly sizing all byte-identical
  `[VERIFIED — git diff touches only the shadow_models array, the added narrative
  keys, the manifest readonly_shadow block, and tests]`.
- The remaining `topdecile_clf_blend_leg` shadow entry is byte-identical.
- `python3 -c "json.load"` parses all three files; prod/golden `shadow_models` and
  retirement keys compare equal `[VERIFIED — this session]`.

## Deliberately NOT touched (and why)

- `configs/strategy_config.shadow.json` (legacy ops-shadow full config, still
  `kind: hf_patchtst`): a standalone file, not the served shadow_models lane this
  decision retires. Whether the orchestrator keeps feeding it is a run-surface
  question owned by the deployment grant, not this config PR.
- `configs/strategy_config.shadow_a.json` / `shadow_b.json`: frozen §2a A/B
  experiment arms; rewriting them mid-protocol VOIDS the running experiment per
  their own pin test.
- `panel_scoring.shadow_experiment` key: bookkeeping tag under which the remaining
  clf shadow leg records; renaming it would change shadow bookkeeping out of scope.
- Historical narrative keys (`_2026_06_05_patchtst_promotion`,
  `_2026_06_23_xgb_promotion`, manifest `supersedes` /
  `promotion_boundary.previous_primary_model_family` / `follow_up_exit_criteria`):
  history, preserved.

## Tests

`make test`: **93 passed, 1 skipped, 1 failed**
`[VERIFIED — this session]`. The one failure
(`tests/test_config_drift.py::test_config_drift_cli_exposes_repo_root`) is
**pre-existing and environmental**, not from this change: it fails identically on
clean `origin/main` (stash-verified) and in the operator's main checkout —
`python3 -m renquant_strategy_104.config_drift` raises ModuleNotFoundError under the
system Python 3.9 subprocess `[VERIFIED — this session, ran all three]`.

## Revert

`git revert` of this PR's merge commit restores the lane entry, the manifest
`readonly_shadow` block, and the previous test pins in one step. No artifact or state
files are involved.
