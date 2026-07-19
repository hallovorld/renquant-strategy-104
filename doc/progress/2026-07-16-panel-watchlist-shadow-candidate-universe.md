# Panel Watchlist Shadow Candidate Universe

STATUS: pending activation; shadow-only configuration and its isolation test
are complete. This record does not authorize a production configuration
change or live-buy admission.

WHAT: `configs/strategy_config.shadow.json` sets
`ranking.panel_scoring.candidate_universe` to `watchlist`. With the existing
shadow-only `enabled=true` and `bypass_ticker_gate=true` flags, the pinned
pipeline may score an eligible, unheld watchlist name even when that name has
no per-ticker tournament artifact. Production and golden configurations keep
the key absent. The test asserts all three invariants.

WHY / DIRECTION: The 104 incident showed that a per-ticker artifact admission
rule can collapse an otherwise viable panel candidate universe. This change
measures the candidate-entry alternative under readonly execution. It changes
neither model features nor weights, does not relax P-WF-GATE, and cannot be
used as evidence for a production promotion.

DEPENDENCY CHAIN:

1. renquant-pipeline #201 supplies the guarded runtime reader.
2. RenQuant #479 pins that pipeline revision and is merged.
3. This strategy PR must merge.
4. A follow-up umbrella pin advance must pin this exact strategy revision and
   refresh the runtime snapshot. Until then the daily shadow leg reads the
   older strategy snapshot and this experiment has not begun.

The rollback runner may use an umbrella-local legacy shadow configuration
without this reader. Such a run is safe but is not evidence for this treatment.

EVIDENCE: `pytest -q tests/test_strategy_configs.py` passes with 31 tests at
the configuration head. The production, golden, shadow-a, and shadow-b
surfaces remain on the legacy candidate-entry rule; only the readonly shadow
configuration carries `candidate_universe=watchlist`.

NEXT: After the strategy pin advance, run readonly-alpaca shadow sessions with
a frozen run bundle. Before any proposal to change production, record and
freeze: candidate coverage and exclusion reasons, finite-score coverage and
calibrated expected-return distribution, veto and QP feasibility rates,
turnover and modeled/realized costs, decision traces, and the comparison to
the legacy candidate universe. The verdict must include predeclared sample
duration and stopping criteria; no result from this configuration alone can
override the diagnostic-only production buy gate.
