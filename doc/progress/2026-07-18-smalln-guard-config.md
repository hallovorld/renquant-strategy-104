# Progress: small-n guard config activation keys (stage 2)

Date: 2026-07-18

## What

Add `buy_floor_min_n: 12` and `buy_floor_absolute_smalln: 0.50` to
`ranking.panel_scoring` in `configs/strategy_config.json` — the stage-2
activation half of the approved VetoWeakBuys small-n guard (RFC
renquant-pipeline#204; implementation renquant-pipeline#205, merged;
evidence renquant-orchestrator#543 + #544).

## Effect

None until the daily deployment pins bump to a pipeline commit
containing #205: the keys are read only by the new guard code. Once
live: scans with fewer than 12 finite-scored candidates get the
relax-only floor max(0.20, min(status-quo floor, 0.50)) — one-sided
(can only widen admission), fixing the 07-16/07-17 all-veto freeze
(floor > max score at n=5). Normal-n behavior bit-identical. The
golden/shadow configs are deliberately untouched (guard absent →
status quo; shadow arms are epoch-frozen).
