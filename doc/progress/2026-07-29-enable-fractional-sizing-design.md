# Progress: design proposal to switch on fractional sizing (sign-off required)

STATUS:   proposal only. NO config changed. The change is a live capital gate.
          Substantially revised this session: (1) the config/runtime
          discrepancy flagged as unresolved is now resolved — it was a
          stale umbrella-tree snapshot, not a live disagreement; (2) a
          major finding — a more rigorous, already-reviewed enablement
          contract for this EXACT change exists from 2026-07-12, staged
          but never merged to `main`. This document's own checklist is
          NOT a substitute for it. Relocated from `renquant-orchestrator`
          per codex BLOCKER: the canonical config this proposes to change
          is owned by `renquant-strategy-104`, not orchestration.

WHAT:     `doc/design/2026-07-29-enable-fractional-sizing.md` — proposes adding
          `execution.fractional_shares` to strategy-104's config, with the
          measured case, what it does NOT fix, the newly-found prior
          contract, six named risks, a pre-flight checklist, and rollback.

WHY/DIR:  S-FRAC v2 is built, merged and pinned in the pipeline;
          `kernel/sizing.py:204` says there is no behaviour change unless
          strategy-104 opts in, and strategy-104's `execution` block does not
          contain `fractional_shares` at all today. This is NOT a first-time
          question, though — see EVIDENCE below.

EVIDENCE: artifact: `RenQuant/logs/daily_104/2026-07-*.log`; live
                    `renquant-strategy-104/configs/strategy_config.json`
                    (the pinned subrepo copy the daily run actually reads,
                    per `model_freshness_monitor.py:279` and
                    `subrepos.lock.json`'s pin `8402a629`);
                    `renquant-pipeline/kernel/sizing.py`; and, newly this
                    session, `renquant-strategy-104` commits `eba5a36`
                    (2026-07-10 operator enablement decision) and `2d2f43e`
                    (the staged-but-unmerged 2026-07-12 enablement
                    contract, branch `config/operator-enablement-batch-1`)
                    — all READ-ONLY.
  prod or exp:      PROPOSAL. No production config, code, or artifact changed.
  existing data:    Yes, measured this session. Size-zero skips per session:
                    07-02 (2), 07-10 (1), 07-13 (2), 07-27 (2), 07-28 (1);
                    deployment 2.8% / 8.8% / 6.7% / 5.0% / 0% of available
                    cash. Names floored: TSLA $309.22, EME $742.73, SPG
                    $236.69.
  best-known?:      Yes for the defect and the config baseline (now
                    resolved, see below). NOT yet known: whether the
                    2026-07-12 contract's 9 prerequisites are now met — one
                    was spot-checked (still unmet as of this session); the
                    other six were not re-checked.
  scope:            One design doc + this progress doc, relocated. No pin
                    advanced, no config edited, no live surface touched.

THE HONEST PART:
          Fractional would have taken 2026-07-27 from $463 to roughly $925 —
          still only ~10% of available cash. The larger constraint is the
          target itself: Kelly produced 6.1% average, the emitted orders
          carried 2.2% after conviction scaling. Fractional does not touch
          that. The doc says so in its own §3 rather than letting a signer
          infer a bigger win than the measurement supports.

          Config/runtime discrepancy — RESOLVED, was NOT a live baseline
          problem: the "config says 0.5" reading came from a stale
          umbrella-tree snapshot copy (`RenQuant/backtesting/renquant_104/
          strategy_config.json`, last synced 2026-07-26 06:30), not the
          file the live pipeline actually reads. At the pinned commit
          (`8402a629`), `kelly_sizing.fractional = 0.3`, matching the
          runtime log exactly. Live config and live runtime agree.

          A more important finding, not in the original revision at all:
          an operator risk decision to enable fractional shares was already
          recorded once, 2026-07-10 (`eba5a36`). Review over several rounds
          walked the flag back to OFF and staged a full enablement contract
          instead (`2d2f43e`, `doc/progress/2026-07-12-fractional-shares-
          enablement.md`) — stop-coverage and execution-liveness invariants,
          a gross fractional-notional cap, an 8-metric monitoring contract,
          named kill/rollback triggers. That branch was never merged to
          `main`; the contract is orphaned, not superseded, and this
          proposal's own (much shorter) checklist does not cover the risk
          that contract exists specifically to bound: fractional positions
          get no broker-side GTC stop on Alpaca, so a dead evaluator process
          is the actual failure mode, not addressed anywhere in this
          document's original risk list.

NEXT:     Operator sign-off is the gate, and per the newly-found contract,
          it is gated FIRST on re-checking that contract's 9 prerequisites
          against current state (one spot-checked this session, still
          unmet) — not on this document's own shorter checklist alone.
          Then: choose `min_notional` deliberately, run a full-funnel sim
          with the flag on vs off using a corrected comparison criterion
          (not "no existing order changes" — see the design doc §7), and
          confirm exit/tax-lot paths accept fractional quantities.
