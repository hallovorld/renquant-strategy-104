# intraday_decisioning config keys — arms the 105 Stage-1 SHADOW landing

STATUS:   CONFIG-ONLY change on branch `feat/intraday-decisioning-config`.
          Defines the top-level `intraday_decisioning` section consumed by
          renquant-orchestrator #266 (`intraday_session_scheduler.
          load_intraday_config`, merged; RFC #208 §8.3/§10) in all three
          policy files: `strategy_config.json`, `strategy_config.golden.json`,
          `strategy_config.shadow.json`. This is #266's landing-checklist
          step 3 CONFIG half ("set `intraday_decisioning.enabled: true` in
          the pinned strategy config").
OUTCOME:  The Stage-1 shadow scheduler's control plane is now declared in
          policy instead of living only in the scheduler's dataclass
          defaults. Merging this changes NOTHING running today: the scheduler
          is a SEPARATE process that nothing in the daily run invokes, and it
          is triple-gated — pinned config `enabled` (this PR) AND env kill
          switch `RENQUANT_INTRADAY_DECISIONING` truthy AND kill-switch file
          absent. The env flag + launchd plist install are machine-side,
          separately authorized ask-first landing steps; until then this
          section is inert by construction.
KEYS:     intraday_decisioning.enabled=true, mode="shadow", tick_seconds=720
          (§5 fixed 12-min Stage-1 cadence), entry_open_delay_seconds=300
          (no entries in the first 5 min), entry_close_cutoff_seconds=1800
          (no NEW entries in the last 30 min; exits run to the bell),
          canary_allowlist=[] (no per-ticker restriction while shadow-only),
          kill_switch_file=null (scheduler default
          `<data_root>/data/rq105/intraday_decisioning.KILL`, re-checked
          every cycle so touching it halts mid-session) — exactly the key
          set `load_intraday_config` reads, every value mirroring its safe
          default, so defining the keys changes no scheduler behavior. The
          section's one real bit is `enabled=true`.
WHY TRUE: An in-pipeline flag defaulting ON would change the next daily run
          at merge — that is why the house flag-discipline precedent
          (`sleeve`, `bear_defensive_sleeve`) ships enabled=false. This flag
          differs structurally: it gates a process that does not exist on the
          machine yet (no plist installed, env flag unset), so enabled=true
          is the CONFIG half of an explicitly sequenced landing, not a
          behavior change. Shipping it false would make the ask-first landing
          step silently insufficient (install the plist, still no ticks) and
          would put the eventual "true" flip inside the machine-landing batch
          where no PR review sees it. Deployed-but-dark lesson: the
          path-to-live is designed here — pin bump -> authorized install ->
          first shadow session -> replay audit (#266 checklist).
SHADOW:   mode="shadow" is the ONLY implemented mode. #266 runtime-asserts
          never-submit on EVERY tick (`assert_shadow_never_submits` raises
          `ShadowModeViolation` before the record persists) and structurally
          DOWNGRADES `mode: "live"` to shadow with a counted warning
          (`live_mode_downgraded_count`, §9.3a). Stage-2 authorization is a
          separate future decision; the new test pins `mode == "shadow"` so
          any flip to "live" fails this repo's suite until that decision
          deliberately rewrites the pin — the authorization bar is
          mechanically visible, not a convention.
SCOPE:    ONLY the new `intraday_decisioning` section (+ its `_comment`
          provenance) and one new pinning test. No existing key touched —
          watchlist, slot counts, mu_floor, kelly, risk knobs, panel/scorer
          contracts all unchanged.
LOCKSTEP: `test_active_and_golden_semantic_config_match` requires active and
          golden to agree on every non-`_` key, so the section is added to
          BOTH production policy files with identical values, and mirrored
          into `strategy_config.shadow.json` per the optional-section house
          pattern (`sleeve` / `bear_defensive_sleeve` precedent, PR #39).
TESTS:    `tests/test_strategy_configs.py::
          test_intraday_decisioning_keys_match_scheduler_defaults_and_stay_shadow_only`
          pins: enabled=true, mode=shadow (the Stage-2 bar), every timing
          key at the scheduler default, empty canary allowlist, null
          kill-switch path, #208+#266 cited in `_comment`, and the EXACT key
          set (no stray keys — the scheduler ignores unknown keys, so a typo
          would silently do nothing). Full suite green — see PR.
NEXT:     After merge (per #266's landing checklist, all ask-first):
          (1) bump the strategy-104 pin in the orchestrator + sync the
          pinned run checkout; (2) machine landing: uncomment
          `RENQUANT_INTRADAY_DECISIONING=1` in the wrapper, copy +
          `launchctl bootstrap` `com.renquant.rq105-session-scheduler.plist`;
          (3) provide `--data-manifest`/`--artifact-manifest` JSONs;
          (4) run `intraday_replay_audit` on the first shadow session —
          a clean report starts the §9.3 K=5 readonly clock.
