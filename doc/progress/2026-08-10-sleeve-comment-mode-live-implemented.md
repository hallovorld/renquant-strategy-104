# Fix stale sleeve._comment: mode=live IS implemented (safety-relevant)

STATUS:    docs/comment-only change to strategy_config.json's `sleeve._comment`.
           BEHAVIOR-INVARIANT — no config value changes; `mode` stays "shadow".

WHAT:      `configs/strategy_config.json` `sleeve._comment` said
           "(mode=live is reserved/unimplemented in #157 and falls back to
           shadow with a warning)". That is FALSE against the current pinned
           code: `renquant-pipeline .../kernel/pipeline/task_parking_sleeve.py`
           implements `mode="live"` as the RS-1 §2/§4 SGOV-floor arm — it emits
           REAL SGOV order intents and FAIL-CLOSES (no order) when SGOV is
           unpriced (docstring :39-47 "Live = SGOV floor only … SPY arm stays
           DARK … deliberately no config knob"; :783-784 sgov_only=True,
           spy_qty=0; :858 sgov_price_missing_live_fail_closed). Corrected the
           comment to state that mode=live is a LIVE-CAPITAL change (not a
           shadow no-op), that the SPY arm is dark with no knob, and that SGOV
           is currently unpriced so live fail-closes to $0 until a price feed is
           wired.

WHY/DIR:   Safety-relevant staleness: an operator/agent reading the old comment
           would believe flipping `mode="live"` is an inert shadow-logging flip,
           when the code actually attempts live SGOV order emission. Surfaced by
           the 2026-08-10 cash-drag backtest (which established that mode=live is
           NOT the SPY-deployment remedy — it is SGOV-only and today a
           fail-closed no-op).

EVIDENCE:  artifact:      configs/strategy_config.json (sleeve._comment) [VERIFIED
                          — JSON re-parses; 1-line targeted replace, no value
                          change; mode stays "shadow"]
           prod or exp:   comment-only; behaviour-invariant; not a deploy
           existing data: renquant-pipeline task_parking_sleeve.py:39-47/783/858
                          (the live SGOV-floor implementation the comment denied)
           best-known?:   yes — states what the code does; removes a footgun
           scope:         one comment string + this doc

TESTS:     json.loads() re-parse OK; no behavioural code path touched.

NEXT:      codex review + merge. Any actual mode=live decision remains gated
           (SGOV pricing wiring + RS-1 §4 for the SPY arm) — unchanged by this.
