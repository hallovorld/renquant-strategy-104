# Drop the dangling walkforward.manifest_path from every carrier (#101)

STATUS: config hygiene, runtime-inert by verified construction.

WHAT: the active config, its six prod-mirror lanes, and shadow_vol_window all
carried `walkforward.manifest_path` pointing at
`…/sim/walkforward_manifest_dropsenti_v3.json` — a file with ZERO hits
anywhere in the live umbrella [VERIFIED 2026-08-24, `find`]. The semantic-
match test even pinned the dangling path as a contract. All nine carriers
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
