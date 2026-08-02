# 2026-08-02 — momentum entry: declare the machine-produced-ledger state

STATUS: complete

WHAT: `_2026_08_02_machine_produced_ledger` narrative key added to the
momentum shadow entry in both configs (+ the prod/golden expected literal in
tests). The key names the TRUE current state: the ledger + dated artifacts
are run-surface outputs of the weekly TRAIN job on the serving machine,
never committed — hosted CI runners cannot resolve the path BY DESIGN.

WHY/DIR: RenQuant#556's verify-pinned-paths red exposed the gap — s104#77
only passed hosted CI through the pending-first-artifact marker's admission,
and #78 correctly retired that marker as false after the first publish. The
umbrella gate now admits exactly this declared state as INFO (RenQuant#557,
inside #554's momentum-contract narrowing, inert wherever the ledger
resolves); this PR supplies the declaration.

EVIDENCE:
- artifact: this PR's diff; suite 96 passed, 1 skipped, 1 pre-existing
  environment failure (test_config_drift_cli_exposes_repo_root, identical on
  clean origin/main)
- prod or exp: reviewed config + test surfaces only
- existing data: the #556 CI log (1/22 fail = exactly this path on the
  hosted runner)
- best-known?: yes
- scope: one narrative key + the expected literal; artifact_path/kind and
  all other entries untouched

NEXT: RenQuant#556 re-pins to this tip + regenerates the snapshot →
machine sync.
