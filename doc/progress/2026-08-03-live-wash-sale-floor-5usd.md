# Live wash-sale materiality floor = $5.00 — the operator's explicit decision

**Date:** 2026-08-03 · `renquant-strategy-104`

STATUS:    live-config change (capital-affecting at the buy-admission margin),
           made on the operator's explicit verbatim decision; deploys via the
           dual s104 sync after merge.
WHAT:      `wash_sale_min_material_npv: 5.00` in strategy_config.json AND
           strategy_config.golden.json (lockstep — golden is the daily drift
           reference; diverging fires the WARN every run). A buy blocked by a
           prior loss sale is RELEASED when the wash-sale NPV tax cost is
           below $5.00; blocks at ≥ $5.00 stand. Tax REPORTING unchanged.
WHY:       Operator 2026-08-03, verbatim: 「低于 $5 放行」— given in direct
           response to "wash sale不能全部杀死，要科学地看成本分析否则就没法玩了".

EVIDENCE (the promotion criteria the shadow de-scope named, all met):

```
mechanism:  pipeline#251 MERGED; A/B byte-invariance proven at floor 0
            (incl. on the real 07-28 incident table)  [早前实测]
shadow run: $1.00 floor live on all shadow lanes since 2026-08-02; measured
            per-block NPV costs $0.04-$0.99 (every one would release at $5)
            [早前实测·今日 blend 日志]
harm basis: 07-28 incident — mass blocks zeroed buys on 3 of 5 sessions
            protecting ~$15 of tax across 8 names while $6.8k cash idled
            [早前实测]
scope:      "live + golden configs, the two floor tests, this doc; the
             shadow lanes keep the stricter $1 evidence floor; the momentum
             shadow lane is tax-free by its own reviewed delta (#82)."
```

## Test contract updates (each a deliberate reversal, named)

- `test_live_and_golden_leave_the_floor_UNSET` → `test_live_floor_is_the_
  operator_decision_and_golden_stays_unset` (pins exactly 5.00 on BOTH; a
  different value is a NEW operator decision, not a tweak).
- Blend semantic-pin: the blend-vs-prod floor delta is now $1 vs $5
  (value-vs-value, still declared) instead of $1 vs ABSENT.

## Revert

git revert + dual re-sync; the binary block returns (with its measured harm).
