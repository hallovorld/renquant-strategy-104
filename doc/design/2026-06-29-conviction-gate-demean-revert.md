# Conviction-gate: revert `demean_cross_sectional` to OFF

**Date:** 2026-06-29
**Status:** PROPOSAL (awaiting Codex review) — NOT yet deployed
**Change:** `ranking.panel_scoring.conviction_gate.demean_cross_sectional`: `true` → `false`
(`mu_floor: 0.03` and `enabled: true` unchanged)

## 1. Summary

The fundamentals-feed freshness bug was fixed and deployed live today (2026-06-29);
`P-FUND-FRESHNESS` now passes. But the live daily-full run
(`run_id 2026-06-29-live-5970796e`) placed **0 buys**.

Root cause: the panel `ConvictionGateTask`. With `demean_cross_sectional: true` the
gate requires `(mu - xs_mean) >= mu_floor`, i.e. it imposes an **absolute** 3%
bar (`mu_floor=0.03`) on a now-**relative** quantity (deviation from the universe
mean). On the fresh feed the cross-sectional mean is large enough (`xs_mean = +0.0212`)
that even the single strongest name clears the floor by less than the gap — so the
gate structurally admits zero. This is a `demean` + `mu_floor` scale mismatch, not a
model or data failure. Both XGB (prod) and PatchTST (shadow) hit the identical wall.

## 2. The exact funnel from the live run (`2026-06-29-live-5970796e`)

```
69 tickers
  - wash-sale            -4   → 65
  - RealizedVolGate     -22   → 43   (drops names with >60% annualized realized vol)
  scored                       43
  - VetoWeakBuys        -37   → 6    (rank floor = mean + 1σ = 0.587)
  - ConvictionGate       -6   → 0    (demean ON, mu_floor 0.03, xs_mean = +0.0212;
                                       top name FTNT: mu 0.0505 → demeaned 0.0293 < 0.03)
  buys                          0
```

All 6 names that survived the upstream `VetoWeakBuys` rank floor were dropped by the
demeaned conviction gate. The strongest candidate, FTNT, had raw `mu = 0.0505`; after
subtracting `xs_mean = +0.0212` it became `0.0293`, which is below `mu_floor = 0.03`.

## 3. Why `demean` + absolute floor is a scale mismatch

`demean_cross_sectional` subtracts the full cross-sectional mean of `mu` before the
floor, turning `mu` into a **relative** quantity — a deviation from the universe mean.
But `mu_floor = 0.03` was set as an **absolute** 3% excess-return bar
(`E[R - SPY] >= 3%`, renquant-pipeline #140). Requiring 0.03 *above the universe mean*
demands more conviction than the model's **daily maximum** `mu` (~0.05) can usually
clear once a positive `xs_mean` is subtracted. On any day where
`xs_mean >= (max_mu - 0.03)` the gate admits zero — a structural zero-buy condition,
not a quality decision.

It is also **redundant**: the stack already filters the relative tail twice — once at
`VetoWeakBuys` (rank floor = mean + 1σ) and again at the demeaned conviction gate. A
single relative tail filter is enough; stacking a relative gate on top of a relative
gate compounds into a near-empty admit set.

## 4. Why the 2026-06-24 validation was invalid

The demean was enabled 2026-06-24/25 (renquant-pipeline #145 + footgun-fix #147) as an
operator-approved **monitored exception** to remove a `+0.0245` calibration intercept,
with an explicit revert clause. Its admission behaviour was "validated 2026-06-24
across 20 live runs (0/20 zero-buy days)". **But the fundamentals feed was frozen at
2026-03-31 throughout that entire window.** That validation therefore ran on stale
data: the `xs_mean` it observed was a stale-feed artifact, not today's fresh-feed
`xs_mean`. On the now-fresh feed the same gate structurally admits zero. The
"0/20 zero-buy days" result does not transfer and is invalid for the current feed.

## 5. The sim-data validation attempt and why it is untrustworthy

To calibrate the floor empirically we tried to score 2 years of
`candidate_scores × realized forward returns`. The only realized data available is
**SIM (backtest)** runs, and their IC **grows with horizon**:
`fwd_5d +0.06 → fwd_20d +0.23 → fwd_60d +0.25`. IC that increases monotonically with
horizon is the signature of train/test look-ahead and/or rally-beta contamination, not
a trustworthy out-of-sample signal. Genuinely out-of-sample **LIVE** runs only begin
2026-04-22 and have **zero** realized `fwd_60d` yet (need ~60 trading days → ~Aug 2026).
A clean data-driven floor calibration is therefore not yet possible and is deferred to
the decision ledger.

## 6. Decision

**Revert `demean_cross_sectional` to OFF now.** This:
- restores buys immediately (the gate returns to `raw mu >= 0.03`);
- returns to a **known-prior trading config** (the pre-2026-06-24 state);
- is consistent with the monitored-exception's own **revert clause** — the structural
  zero-buy on the fresh feed is exactly the failure mode the exception reserved the
  right to roll back.

**Alternative considered:** keep `demean` ON and lower `mu_floor` to a round-trip
transaction-cost hurdle (~0.005). **Rejected for now** because the exact hurdle value
cannot be validated until live forward returns realize (~Aug 2026), and reverting to
the known-prior config is the lower-risk move. We can revisit the absolute-floor
calibration (intercept-gating vs cost-hurdle) once clean data exists.

## 7. Validation plan

- The decision ledger (separate renquant-pipeline PR, #133 wiring) captures live
  `raw + mu + selected + realized-fwd` starting from today's runs.
- Revisit the absolute-floor calibration ~Aug 2026, when live `fwd_60d` has realized
  (~60 trading days after the 2026-04-22 first clean OOS run), using genuinely
  out-of-sample forward returns rather than look-ahead-contaminated sim IC.
- At that review, decide between: (a) keep raw `mu_floor = 0.03`; (b) lower the floor
  to a measured round-trip cost hurdle; (c) re-enable demean only if it demonstrably
  improves realized forward returns.

## 8. Reversibility

Flip the one boolean back: `demean_cross_sectional: false → true`. No artifact,
calibrator, or pin changes are involved.
