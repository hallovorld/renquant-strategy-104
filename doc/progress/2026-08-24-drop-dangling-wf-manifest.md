# Drop the dangling walkforward.manifest_path from every carrier (#101)

STATUS: config hygiene, runtime-inert by verified construction.

WHAT: the active config, its six prod-mirror lanes, and shadow_vol_window all
carried `walkforward.manifest_path` pointing at
`…/sim/walkforward_manifest_dropsenti_v3.json` — a file with ZERO hits
anywhere in the live umbrella [VERIFIED 2026-08-24, `find`]. The semantic-
match test even pinned the dangling path as a contract. All eight changed carriers (the golden config was already absent and is covered by the test assertion only)
now drop the block; the test asserts BOTH surfaces declare no walkforward
block, with reintroduction requiring a reviewed edit of that assertion.

WHY inert (§4b): `SimAdapter._try_load_walkforward_loader` enters only on
`walkforward.enabled=True` — the key is absent in every carrier, and the
default is False [VERIFIED — read at head]; the live `RunnerAdapter` has no
`walkforward.*` reads at all [VERIFIED — grep]. External consumers
(concentration sweep, kelly A/B, modal cloud runner) all `setdefault` their
OWN walkforward block into their own config copies and never require the
key in these files [VERIFIED — grep of orch + umbrella scripts].

Frozen-arm note: shadow_vol_window's prereg froze WINDOW CONSTANTS; a
dangling, runtime-inert pointer is not part of the arm's measured
definition, and its behavior is byte-identical with the block absent
(the loader path is never entered either way).

§4b: full suite **103 passed, 1 skipped** (pre-existing skip) on
CI-matching py3.10. Closes #101.


## Authority + identity note (review r2, 2026-08-27)

- This change is **behaviorally equivalent but NOT fingerprint-inert**: it
  changes the bytes of `configs/strategy_config.json` and seven shadow
  carriers, so run-bundle/provenance fingerprints of strategy config change
  intentionally. It is treated as a production-config write, not a no-op.
- Operator authorization received 2026-08-26, verbatim 「授权 row 2c」 (item 3
  of the five-item authorization batch, Claude operator session); the
  corresponding LONG-ledger **row 2c** lands in renquant-orchestrator before
  this PR merges (sequenced after orch#1049/row 2b to avoid same-table
  conflicts).
- Deploy after merge follows the normal ordered path: umbrella pin advance +
  runtime sync as separate reviewed steps, so runtime identity and provenance
  stay coherent.
- Carrier-count correction: the diff changes **eight** config carriers; the
  golden config never carried the key and is covered by the test assertion
  only.
