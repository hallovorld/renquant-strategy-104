# Operator authorization: diagnostic-only buy admission (bounded)

Date: 2026-07-16

## What

Adds `wf_gate.diagnostic_only_buy_admission` to the active + golden
strategy configs: an explicit, auditable, EXPIRING authorization for the
preflight P-WF-GATE to admit buys while the active scorer's WF evidence is
diagnostic-only.

- operator: renhao (directive 2026-07-16, continuing 2026-06-22
  "全放宽 + 上 XGB")
- expires: 2026-08-15 (hard stop; gate reverts to sell-only)
- bound to ONE scorer: v1 content hash sha256:656b70be… (the 2026-06-21
  XGB panel). Any model swap invalidates the authorization automatically.

## Why

The 2026-07-15 admission gate (renquant-pipeline, codex-reviewed) blocks
ALL buys for diagnostic-only scorers with no override path. Combined with
the chronic weekly WF-promote placebo-subgate rejects, the book drained to
94% cash (incident 2026-07-16). This entry is the governed alternative to
an ungoverned bypass: identity + expiry + scorer binding + reason, in a
pinned, reviewed config.

## Mechanism

Consumed by the renquant-pipeline preflight gate (companion PR adds the
mechanism: fail-closed on any malformed field, expiry checked per run,
scorer hash verified against the loaded artifact, full provenance attached
to the run bundle). Config-fingerprint subset is unaffected (the new key is
outside `config_fingerprint_fields`).

## Tests

Repo suite: 80 passed; 1 pre-existing local env failure
(`test_config_drift_cli_exposes_repo_root`, fails identically on
origin/main — Python 3.9 subprocess env, unrelated).
