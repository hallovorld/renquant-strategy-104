# Progress: design proposal to switch on fractional sizing (sign-off required)

STATUS:   proposal only, revised. NO config changed. Moved from
          `hallovorld/renquant-orchestrator#607` (codex review, 2026-07-29:
          wrong repo — this is strategy-104-owned policy) and substantially
          corrected in the move: two of the original doc's central claims
          were measured against the umbrella's stale config copy rather than
          this repo's pinned one.

WHAT:     `doc/design/2026-07-29-enable-fractional-sizing.md` — proposes
          flipping `execution.fractional_shares.enabled` from `false` to
          `true` in this repo's pinned config, with the measured case, an
          explicit list of what it does NOT fix, a sequencing conflict
          against this repo's own agreed cash-drag execution order, five
          named risks, a pre-flight checklist, and rollback.

WHY/DIR:  S-FRAC v2 is built, merged and pinned in the pipeline;
          `kernel/sizing.py:204` (renquant-pipeline) says there is no
          behaviour change unless strategy-104 opts in. This repo's pinned
          config already declares the `fractional_shares` block (added
          2026-07-07 alongside the S-FRAC v2 stage-2 sizing contract) but
          keeps it OFF pending "the active-path capability gate, broker
          guard, and sizing-fidelity evidence."

EVIDENCE: artifact: `RenQuant/logs/daily_104/2026-07-*.log`,
                    `configs/strategy_config.json` /
                    `.golden.json` (this repo, `main`),
                    `renquant-pipeline/kernel/sizing.py`,
                    `tests/test_strategy_configs.py`,
                    `renquant-orchestrator doc/design/2026-07-07-104-105-cash-drag-resolution.md`,
                    `renquant-strategy-104 doc/progress/2026-07-12-one-share-floor-enablement.md`
                    — all READ-ONLY.
  prod or exp:      PROPOSAL. No production config, code, or artifact
                    changed.
  existing data:    Yes, measured this session
                    [VERIFIED — this session, `python3 -c` reading both
                    `configs/strategy_config.json` and `.golden.json` on a
                    freshly-pulled `main`]. Size-zero skips per session
                    (carried from the original draft, not re-measured this
                    session): 07-02 (2), 07-10 (1), 07-13 (2), 07-27 (2),
                    07-28 (1); deployment 2.8% / 8.8% / 6.7% / 5.0% / 0% of
                    available cash. Names floored: TSLA $309.22, EME
                    $742.73, SPG $236.69
                    [VERIFIED — prior session, `RenQuant/logs/daily_104/
                    2026-07-*.log`, carried forward from
                    `renquant-orchestrator#607`'s original evidence, not
                    independently re-measured here].
  best-known?:      Yes for the defect and the (corrected) config state.
                    The impact estimate is `[DERIVED]` and deliberately
                    conservative — see the design doc §3.
  scope:            One design doc + this progress doc. No pin advanced, no
                    config edited, no live surface touched.

THE HONEST PART:
          Fractional would have taken 2026-07-27 from $463 to roughly $925 —
          still only ~10% of available cash. The larger constraint is the
          target itself: Kelly produced 6.1% average, the emitted orders
          carried 2.2% after conviction scaling. Fractional does not touch
          that. The design doc says so in its own §3.

          This proposal is Phase 3 of this repo's own agreed cash-drag
          execution order (`renquant-orchestrator
          doc/design/2026-07-07-104-105-cash-drag-resolution.md`), which
          explicitly requires the cheaper Phase 2 one-share initiation floor
          (A-3) — already built and tested, with its own enablement
          contract on record — to be "exhausted or shown insufficient"
          first. A-3 is also still OFF
          [VERIFIED — `configs/strategy_config.json` and `.golden.json`,
          `sizing.one_share_floor_enabled: false` in both, read this
          session]. This document does not resolve that sequencing
          question; it surfaces it for the operator (design doc §4).

CORRECTIONS (from the orchestrator-repo original, codex review
`hallovorld/renquant-orchestrator#607`):
  1. **"`execution.fractional_shares` is absent entirely"** — false when
     read against this repo's pinned config; it exists, added 2026-07-07,
     default OFF, pinned by
     `test_fractional_shares_contract_is_explicit_and_default_off`. The
     original claim was measured against the umbrella's stale copy
     (`RenQuant/backtesting/renquant_104/strategy_config.json`).
  2. **"Choose `min_notional`, TBD"** — false; already `1.0`, chosen
     2026-07-07 alongside a `min_fractional_trade_notional=25.0` dust floor.
  3. **"config says `kelly_sizing.fractional=0.5` vs runtime
     `fractional=0.30`, unresolved"** — resolved: two different config
     copies (umbrella-stale `0.5` vs this repo's pinned `0.3`) of an
     unrelated knob (the fractional-Kelly betting fraction, not
     share-quantity fractionality). Not a precondition for this decision.

NEXT:     Operator sign-off is the gate, and per §4 of the design doc the
          operator's decision also covers the sequencing question (jump
          Phase 2→3, or finish A-3 first). Before enablement regardless of
          that answer: re-validate the already-chosen `min_notional` /
          `min_fractional_trade_notional` against current book size, run a
          full-funnel sim with the flag on vs off, and confirm exit/tax-lot
          paths accept fractional quantities. None of that work is done in
          this pass — this pass only corrected the proposal's factual
          premises and re-homed it to the owning repo.
