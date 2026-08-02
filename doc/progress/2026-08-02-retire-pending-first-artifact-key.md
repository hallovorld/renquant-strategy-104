# 2026-08-02 — retire the momentum pending-first-artifact key (batch landed)

STATUS: complete

WHAT: The `_2026_08_02_pending_first_artifact` narrative key deleted from the
momentum shadow entry in `configs/strategy_config.json` and
`configs/strategy_config.golden.json` (surgical line removal, JSON re-validated),
the `PENDING_FIRST_ARTIFACT` bounded set in `tests/test_strategy_configs.py`
shrunk to empty, and the prod/golden expected literal updated — the exact
follow-up the key's own text schedules ("the batch's config-merge step
triggers the follow-up PR that deletes this key and shrinks that set
together").

WHY/DIR: The slice-5 grant batch LANDED 2026-08-02: first artifact + genesis
ledger row published (`artifact_content_sha256 a824c480cd9c…`, 144/144), the
entry merged (#77), the pin advanced (RenQuant#555), and the umbrella gate
narrowed to exactly this entry's contract (RenQuant#554). The declared
pending state now describes a world that no longer exists; a lingering
pending marker over a resolving ledger would teach readers to trust a stale
state (the launchd-manifest PENDING_INSTALL precedent, retired the same way
in orch#762).

EVIDENCE:
- artifact: this PR's diff
- prod or exp: reviewed config + test surfaces only
- existing data: suite 95 passed, 1 skipped, 1 failed —
  `test_config_drift.py::test_config_drift_cli_exposes_repo_root`, reproduced
  identically on clean origin/main with this change stashed (environment-
  dependent, pre-existing, not touched here)
- best-known?: yes — the ledger's existence and the batch landing are
  machine-verified in the orch#759 record and the RenQuant#555 sync log
- scope: the one narrative key + its bounded set + the expected literal;
  `artifact_path`, `kind`, the lane narrative key, and all other entries
  untouched

NEXT: none — rides the next routine s104 pin advance; no urgency (the key is
inert once the ledger resolves).
