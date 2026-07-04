# M6 stage-2 step 1, config half: `fingerprint.accept_legacy_stamps` declared in policy

STATUS:   CONFIG-ONLY change on branch `feat/m6-fingerprint-flag`. Defines
          `ranking.panel_scoring.fingerprint.accept_legacy_stamps: true` in
          all three policy files (`strategy_config.json`,
          `strategy_config.golden.json`, `strategy_config.shadow.json`).
          This is the strategy-104 half of the M6 stage-2 step-1 pair
          (renquant-orchestrator
          `doc/design/2026-07-03-m6-stage2-fingerprint-migration.md` §3
          step 1: "renquant-pipeline PR plus a strategy-104 config PR for
          the flag — policy lives in strategy config, enforcement in
          pipeline"). The pipeline half is MERGED: renquant-pipeline #164
          (`fingerprint_dispatch.accept_legacy_stamps`, absent => true).
OUTCOME:  The M6 migration-window dual-accept flag now exists as an explicit
          policy declaration instead of only a code default. Merging this
          changes NOTHING running today — explicit `true` equals #164's
          absent-key default at both fail-closed enforcement points
          (`job_panel_scoring.py::_assert_calibrator_matches_scorer`,
          `walk_forward/loader.py::_assert_calibrator_matches_entry`). The
          point is making the future flip REVIEWABLE: step 4 of the design
          (`accept_legacy_stamps: false`, v1-only — a versionless stamp
          fails closed with the re-stamp-under-v1 remedy) becomes a one-key
          strategy-config PR with a suite-visible diff, and its rollback is
          flipping the key back.
KEY:      `ranking.panel_scoring.fingerprint.accept_legacy_stamps = true`
          — exactly the path #164's reader walks (`ranking` ->
          `panel_scoring` -> `fingerprint` -> `accept_legacy_stamps`),
          placed adjacent to `global_calibration` (the scorer/calibrator
          identity contract it governs). The section carries a dated
          `_comment` citing the design doc + #164 and naming the step-4
          flip as the future migration act.
TEST:     New `test_fingerprint_accept_legacy_stamps_is_explicit_and_true`
          iterates all three configs and pins: value is `True` (so a flip to
          `false` fails the suite until the step-4 decision deliberately
          rewrites the pin alongside the config — the mechanically visible
          authorization bar, mirroring PR #41's `mode == "shadow"` pin),
          `_comment` cites #164 + the design doc, and the section carries
          exactly {accept_legacy_stamps, _comment} (a typo'd extra key would
          silently do nothing).
SCOPE:    ONLY the new `fingerprint` section (+ `_comment` provenance) and
          one new pinning test. No existing key touched — watchlist, slot
          counts, mu_floor, kelly, risk knobs, panel/scorer/calibrator
          contracts all unchanged.
LOCKSTEP: `test_active_and_golden_semantic_config_match` requires active and
          golden to agree on every non-`_` key, so the section is added to
          BOTH production policy files with identical values, and mirrored
          into `strategy_config.shadow.json` per the house pattern (sleeve
          PR #39, intraday PR #41). The shadow lane matters here in its own
          right: shadow artifacts are first-class census rows in the M6 plan
          (design §5 row 7 — a shadow fail-close is a contract failure that
          can run dark), so the shadow lane's flag state must be declared,
          not inherited.
NEXT:     Design §4 order after this PR (row 5): deploy (pin bumps +
          live pin-align + venv >= 0.9.2, evidence recorded) -> step-2 v1
          re-stamp RUN (operator grant, dry-run first) -> step-3 census
          green over the observation window -> step-4 flag flip (`false`,
          separate config PR rewriting the pin) -> step-5 common 0.10 shim
          removal.
