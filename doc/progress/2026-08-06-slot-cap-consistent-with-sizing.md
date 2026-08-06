# The slot cap assumed 12% positions; the sizing chain can only produce 6.84%   (PR)

STATUS:   delivered — one config value changed. No code, no per-name or sector limit touched.

WHAT:     `max_concurrent_positions` 8 → 13, so the COUNT cap is consistent with the
          largest position the sizing chain can actually produce.

WHY/DIR:  GOAL-5 P0, operator-escalated. The live book has been ~80% idle for 54
          consecutive sessions and simultaneously OVER its position count cap, and
          those two facts have the same root: the count cap was chosen for a
          position size the sizer never produces.

EVIDENCE:
artifact:      `configs/strategy_config.json`; live Alpaca account; kernel
               `sizing.py` / `pipeline/task_selection.py` in the PINNED runtime
prod or exp:   prod
existing data: renquant-orchestrator#866 found the book at 10 positions against a
               cap of 8 (`open_slots` counts filled positions only, so three runs
               on 2026-08-04 each saw `held=5` and their orders accumulated). The
               capital-deployment v2 design measured the sizing cascade. Neither
               reconciled the count cap against the achievable position size.
best-known?:   yes — first measurement of the two together.
scope:         this is the live book on 2026-08-06, prod, and it is a CONSISTENCY
               claim between two config values. It asserts no IC, Sharpe or return
               improvement, and does not estimate whether deploying the idle
               capital makes or loses money.

| quantity | value |
|---|---:|
| regime cap `BULL_CALM.max_position_pct` | **0.12** `[VERIFIED — config]` |
| `confidence_to_size_multiplier(0.57)` — hard-coded, no config knob | **0.57** `[VERIFIED — kernel/regime.py:393, conf from live log]` |
| **hard ceiling on any single position** | **6.84 %** `[DERIVED — 0.12 × 0.57]` |
| live median position | **3.1 %** of equity `[VERIFIED — Alpaca get_all_positions, 2026-08-06]` |
| live invested | **52.7 %** with 10 positions `[VERIFIED — same]` |
| median idle buying power, 54 sessions | **80.9 %** `[VERIFIED — prior audit, orch#877]` |

**8 slots × 6.84 % = 55 %** — the book could not reach full deployment even with
every slot at its ceiling. **13 × 6.84 % = 89 %**, which is what the original cap
of 8 assumed when it was paired with a 12 % position (8 × 12 % = 96 %).

## What is NOT changed

`max_position_pct` (0.12), `max_positions_per_sector` (6), `max_sector_weight_pct`
(0.35) and `CHOPPY.max_concurrent_positions` (4) are all untouched. **No per-name
or sector concentration limit is loosened by this PR.** The only thing that changes
is how many names the book may hold at once.

NEXT:     This unblocks admission; it does not fix the accumulation bug that put the
          book over its cap in the first place — that is renquant-pipeline#269
          (`open_slots` must subtract in-flight accepted-unfilled buys). Both are
          needed: this one so the book can deploy, that one so it stops exceeding
          whatever cap it has.

## What this does NOT establish

- **Not that 13 is optimal.** It is the value that makes the count cap consistent
  with the measured position ceiling. A different fix — raising the position size
  by re-calibrating the stale `conviction ceiling: 0.3`, or exposing the hard-coded
  0.57 confidence multiplier — would imply a different slot count.
- **Not that deploying the idle capital is profitable.** No return estimate is made
  anywhere in this PR.
- **Not that the book will now buy.** Admission also passes through
  `VetoWeakBuysTask`'s relative floor, which admits ~1–3 % of the cross-section
  (measured: 108 scanned → 2 ranked on a typical day).

REVERT:   set `max_concurrent_positions` back to `8` and delete
          `_max_concurrent_positions_reason`.
