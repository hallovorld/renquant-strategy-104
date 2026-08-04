# 2026-08-04 — blend profiles: rotate component[0] pin to the promoted scorer

Both blend shadow lanes fail-closed today ("no trade (panel_scoring_fail_
closed)"): `LoadScorerTask` refused component[0] with `content_sha256 MISMATCH
pinned='sha256:04d7a381cd6df847'` — the profiles pinned the PRODUCTION scorer
by content sha as of 2026-07-27, and the 11:31 PT RFC#210 promotion swapped
the ACTIVE artifact (now `sha256:6461b827ab2339a8`, trained 2026-08-02). The
identity guard worked exactly as designed; the pin is what rotted. This is
the FOURTH consumer of the promotion found by running today (after the
runtime P-WF-GATE twins, the reject-notify tone, and the bundle checker).

Change: `expected_content_sha256` → `sha256:6461b827ab2339a8` in
`strategy_config.shadow_blend.json` + `strategy_config.shadow_blend_momentum.json`
(config fingerprint `f8fb2259…` unchanged — recipe-level, promotion-invariant);
semantic-pin guard test updated with a dated rotation note.

S1 ledger honesty: session 1 (2026-08-04) recorded a fail-closed no-trade
under the stale pin; after this lands + deploys, a same-day Step-5b rerun
produces the session's real decision record (canonical-run selection takes the
later candidate-carrying run).

Standing debt filed in renquant-orchestrator: every RFC#210 promotion must
rotate these pins in the same batch (promotion consumer checklist) — or the
profiles move to config-fingerprint-only pinning with per-session serving
identity (S2 already records identity triplets). Until decided, this manual
rotation is the procedure.

Verification: s104 suite 98 passed, 1 skipped, 1 pre-existing environment
failure (`test_config_drift_cli_exposes_repo_root`, fails identically on
clean main).
