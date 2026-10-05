# Served-scorer content pin follows the A4-T1 promotion (6461b827 → f1b1c132)   (PR #107)

STATUS:    authorized — production-config write under LONG row 2, covered by
           orchestrator LONG row 2g, which is on orchestrator `main`
           (renquant-orchestrator#1115, merged 2026-10-05 UTC at d6719ab4)
           and quotes the operator's 2026-09-12 confirmation of THIS pin
           move verbatim. Landed on the live tree under containment
           2026-09-12; this PR is the reviewed surface and awaits Codex
           re-review against the merged row.
WHAT:      In the SEVEN carriers that pin the blend's component[0]
           (`configs/strategy_config.json`, its golden twin, and the five
           `shadow_blend*` prod-mirror lanes), `ranking.panel_scoring.
           components[0].expected_content_sha256` moves from
           `sha256:6461b827ab2339a8` (the 2026-08-02 model) to
           `sha256:f1b1c1322e3b66f7` (the artifact the umbrella serves since
           2026-09-03 09:09 PDT), with a NAMED sibling key
           `_expected_content_sha256_reason` stating the rotation, the
           candidate/run id, the receipt, and the authority row (named
           explicitly, per the row-2a lesson that an unnamed `_reason` key
           voided an approval). The eighth file that mentions the old digest,
           `configs/zblend_prod_artifact_manifest.json`, is an AUDIT record of
           the 2026-08-04 switch-time identity (prose, not a gate field) and
           is deliberately NOT rewritten. No other key changes.
           `tests/test_strategy_configs.py::test_shadow_blend_profile_semantic_pins`
           fixture updated to the new pin.
WHY/DIR:   The A4-T1 promotion (bt#128 / orch#1110 / RenQuant#632, 2026-09-03)
           replaced the served `artifacts/prod/panel-ltr.alpha158_fund.json`
           bytes (trained 2026-08-31; the orchestrator consumption proof is
           stamped INTO the artifact). The served config has pinned the
           blend's component[0] by content digest since the 2026-08-04
           z-blend override (strategy-104 0bd93d6) — and no promotion had
           happened between 08-04 and 09-03, so the promote chain never
           had to move the pin and has no step for it. On 2026-09-04 06:06
           the dawn funnel preflight (first full funnel probe since the
           promotion) refused the load:
           `LoadScorerTask: failed to load blend artifact … blend component[0]
           content_sha256 MISMATCH … pinned='sha256:6461b827ab2339a8'
           observed=sha256:f1b1c1322e3b66f7…; Panel scoring contract failed
           (panel_scorer_load_failed). Cleared 6 buy candidate(s); buy/QP
           path is fail-closed` — i.e. the 13:55 daily will place NO buys
           even though P-REGIME-IC is licensed (pipeline#308). The pin did
           its job (a swapped file is observable); the promotion is simply
           incomplete without the pin moving. Direction: G-C (the refresh
           path reaches a SERVED outcome) — this is the last link.
           Structural note for the row: every future promotion needs the
           same pin move; the promote chain should either emit the required
           config change as an artifact of the promotion or the pin should
           become the ledger-style identity the momentum leg uses. Out of
           scope here.
EVIDENCE:  artifact:      `RenQuant/logs/rq104/dawn_funnel_preflight_2026-09-04.log` line 227 (the MISMATCH line, pinned vs observed) and line 228 (contract failed, 6 candidates cleared) [VERIFIED — read 2026-09-04 06:3x PDT]; served artifact sha256 prefix `f1b1c1322e3b66f7`, trained 2026-08-31, `promotion_basis=freshness_fallback_rfc210`, A4-T1 run 20260831T141820Z, receipt 2cd9d27b… ; `.previous.json` sha256 prefix `6461b827ab2339a8`, trained 2026-08-02 [VERIFIED — read-only hashlib + json, 2026-09-04 06:3x PDT]
           prod or exp:   prod served config (and its golden + five prod-mirror lanes); the change re-enables the buy path of the live book on the operator-authorized artifact
           existing data: pin history: `git log -S expected_content_sha256 -- configs/strategy_config.json` → 0bd93d6 (2026-08-04 override) and 40640d1 (2026-07-26 clf leg) — no pin move since the 08-04 override; `grep -c 6461b827ab2339a8 configs/*.json` → 8 files, of which 7 carry the KEY and 1 (the manifest) carries the digest only in audit prose [VERIFIED]; test suite in the worktree (umbrella venv): 104 passed, 1 skipped, 1 failed — `tests/test_config_drift.py::test_config_drift_cli_exposes_repo_root` fails IDENTICALLY on the unmodified pinned checkout 7998212 (CalledProcessError from the drift CLI subprocess; pre-existing, unrelated) [VERIFIED — 2026-09-04 between 06:45 and 06:35 PDT]
           proof (read-only): the PINNED pipeline's `load_blend_scorer` (faf1416a, umbrella venv + pinned PYTHONPATH, `_strategy_dir` = the live strategy dir) on the pinned config 7998212 → REFUSED `blend component[0] content_sha256 MISMATCH … pinned='sha256:6461b827ab2339a8' observed=sha256:f1b1c1322e3b66f7…` (the dawn preflight's exact refusal); on THIS PR's `configs/strategy_config.json` → LOADED 2 components (`panel-ltr.alpha158_fund.json` + `momentum_artifact_ledger.jsonl`, both identity-verified) [VERIFIED — 2026-09-04 between 06:50 and 06:37 PDT; no file written]
           best-known?:   n/a — identity bookkeeping; no model claim (the promoted artifact is the zero-trade A4-T1 candidate the standing policy refuses; this PR does not change that decision, it makes the authorized decision executable)
           scope:         "this PR moves one digest pin (and adds its named reason) in seven config carriers and one test fixture; it does not touch any artifact, any other key, or the audit manifest"
NEXT:      row 2g is merged (renquant-orchestrator#1115) → Codex re-review
           of this PR against the merged row → merge this PR → umbrella pin advance
           (`subrepos.lock.json` renquant-strategy-104 → this merge) +
           snapshot re-render → live `git pull --ff-only` +
           `subrepo_assemble --sync` → the next dawn preflight / 13:55 run
           loads the blend (`LoadScorerTask` ok) and the buy path opens.
           Rollback = single-commit revert of this PR + pin advance back.
