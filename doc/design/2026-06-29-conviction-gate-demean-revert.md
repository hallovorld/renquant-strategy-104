# Conviction-gate: revert `demean_cross_sectional` to OFF

**Date:** 2026-06-29
**Status:** PROPOSAL (awaiting Codex review) — NOT yet deployed
**Change:** `ranking.panel_scoring.conviction_gate.demean_cross_sectional`: `true` → `false`
(`mu_floor: 0.03` and `enabled: true` unchanged) — applied to BOTH
`strategy_config.json` (active) and `strategy_config.golden.json` (policy baseline)
so active == golden, with an explicit drift-pinning test
(`test_conviction_gate_demean_is_off_and_mu_floor_pinned`).

This is framed as an **emergency operator-authorized, reversible config rollback**
based on **new fresh-feed evidence**, NOT as the formal ~60d monitored-exception
revert (those metrics are not yet evaluable — see §4 and §6).

## 1. Summary

The fundamentals-feed freshness bug was fixed and deployed live today (2026-06-29);
`P-FUND-FRESHNESS` now passes. 2026-06-29 is the **first fresh / PIT-valid day** for
the fundamentals feed. On that first fresh day the live daily-full run
(`run_id 2026-06-29-live-5970796e`) had a **zero-admission incident**: the conviction
gate admitted **0** of the 6 names that survived the upstream rank floor.

Proximate cause: the panel `ConvictionGateTask`. With `demean_cross_sectional: true` the
gate requires `(mu - xs_mean) >= mu_floor`, i.e. it imposes an **absolute** 3%
bar (`mu_floor=0.03`) on a now-**relative** quantity (deviation from the universe
mean). On the fresh feed the cross-sectional mean is large enough (`xs_mean = +0.0212`)
that even the single strongest name (FTNT, raw `mu=0.0505`) clears the floor only after
the gap is subtracted — `0.0293 < 0.03` — so the gate admitted zero on this date. Both
XGB (prod) and PatchTST (shadow) hit the identical wall on this run.

**Scope / what is NOT claimed.** This is one zero-ADMISSION incident on ONE fresh
PIT-valid date, not an established "structural zero-buy" regime. We argue the
structural risk from the algebra below, but we do NOT yet have a distribution of
`max(mu) - mean(mu)` over many fresh dates (the feed only became fresh today), so we
downgrade the claim accordingly. This document also demonstrates only the **admission
layer**; the full QP sizing/turnover replay is a documented follow-up (§5, §7), not
asserted here.

## 2. The exact funnel from the live run (`2026-06-29-live-5970796e`)

```
69 tickers
  - wash-sale            -4   → 65
  - RealizedVolGate     -22   → 43   (drops names with >60% annualized realized vol)
  scored                       43
  - VetoWeakBuys        -37   → 6    (rank floor = mean + 1σ = 0.587)
  - ConvictionGate       -6   → 0    (demean ON, mu_floor 0.03, xs_mean = +0.0212;
                                       top name FTNT: mu 0.0505 → demeaned 0.0293 < 0.03)
  admitted (demean ON)          0
```

All 6 names that survived the upstream `VetoWeakBuys` rank floor were dropped by the
demeaned conviction gate.

## 3. Demonstrated admission counterfactual (ON vs OFF) on this run

Counterfactual replay over the exact stored bundle (`2026-06-29-live-5970796e`), the 6
post-`VetoWeakBuys` survivors, `xs_mean(mu) = +0.0212`. Demean ON admits when
`(mu - xs_mean) >= 0.03`; demean OFF admits when `mu >= 0.03`:

| name | raw mu  | demeaned (mu − xs_mean) | demean ON | demean OFF |
|------|---------|--------------------------|-----------|------------|
| FTNT | 0.0505  | 0.0293                   | drop      | **ADMIT**  |
| SOFI | 0.0476  | 0.0264                   | drop      | **ADMIT**  |
| NEE  | 0.0435  | 0.0223                   | drop      | **ADMIT**  |
| BLK  | 0.0414  | 0.0202                   | drop      | **ADMIT**  |
| AVGO | 0.0373  | 0.0161                   | drop      | **ADMIT**  |
| CVX  | 0.0365  | 0.0153                   | drop      | **ADMIT**  |

**⇒ ADMITTED: demean ON = 0, demean OFF = 6.**

### Scope and honest limitations (do not over-read this)

- This is **one fresh, PIT-valid date**. The fundamentals feed only became fresh
  2026-06-29, so a **distribution** of `max(mu) - mean(mu)` over many fresh dates is
  **NOT yet available**. We therefore cannot call this a "structural zero-buy regime";
  it is a **zero-admission incident** on the first fresh-feed day.
- The structural risk is **ARGUED from the algebra** (§4: admission needs
  `mu >= xs_mean + mu_floor ≈ 0.0212 + 0.03 = 0.051`, vs the day's max
  `mu ≈ 0.0505`), but is **not established over a distribution**. Establishing it
  requires the decision ledger to accumulate fresh-feed cross sections (~Aug 2026).
- This demonstrates the **ADMISSION layer only**. The full QP sizing / turnover /
  order replay is **NOT run here** and is a documented follow-up (§7). We deliberately
  do **not** assert buys, orders, sizes, or turnover from this counterfactual.

## 4. Why `demean` + absolute floor is a scale mismatch (the algebra)

`demean_cross_sectional` subtracts the full cross-sectional mean of `mu` before the
floor, turning `mu` into a **relative** quantity — a deviation from the universe mean.
But `mu_floor = 0.03` was set as an **absolute** 3% excess-return bar
(`E[R - SPY] >= 3%`, renquant-pipeline #140). Requiring 0.03 *above the universe mean*
demands more conviction than the model's **daily maximum** `mu` (~0.05) can usually
clear once a positive `xs_mean` is subtracted. The admission **condition** is:
admission requires `mu >= xs_mean + mu_floor`. On 2026-06-29 that is
`mu >= 0.0212 + 0.03 = 0.051`, while the day's maximum `mu` was `≈ 0.0505` — so on
**this** cross section the gate admits zero. Whether this recurs (i.e. whether
`xs_mean >= max_mu - 0.03` holds **often** on fresh feeds) is an empirical question we
have **not** answered: it needs a distribution over many fresh-feed dates, which is not
yet available. We present the algebra as the *mechanism* for the observed incident, not
as proof of a persistent regime.

It is also plausibly **redundant**: the stack already filters the relative tail twice —
once at `VetoWeakBuys` (rank floor = mean + 1σ) and again at the demeaned conviction
gate — so stacking a relative gate on a relative gate can compound into a near-empty
admit set. (This too is an argument, to be confirmed against the accumulated ledger.)

## 5. Why the 2026-06-24 validation was invalid

The demean was enabled 2026-06-24/25 (renquant-pipeline #145 + footgun-fix #147) as an
operator-approved **monitored exception** to remove a `+0.0245` calibration intercept,
with an explicit revert clause. Its admission behaviour was "validated 2026-06-24
across 20 live runs (0/20 zero-buy days)". **But the fundamentals feed was frozen at
2026-03-31 throughout that entire window.** That validation therefore ran on stale
data: the `xs_mean` it observed was a stale-feed artifact, not today's fresh-feed
`xs_mean`. On the now-fresh feed the same gate structurally admits zero. The
"0/20 zero-buy days" result does not transfer and is invalid for the current feed.

## 6. The sim-data validation attempt and why it is untrustworthy

To calibrate the floor empirically we tried to score 2 years of
`candidate_scores × realized forward returns`. The only realized data available is
**SIM (backtest)** runs, and their IC **grows with horizon**:
`fwd_5d +0.06 → fwd_20d +0.23 → fwd_60d +0.25`. IC that increases monotonically with
horizon is the signature of train/test look-ahead and/or rally-beta contamination, not
a trustworthy out-of-sample signal. Genuinely out-of-sample **LIVE** runs only begin
2026-04-22 and have **zero** realized `fwd_60d` yet (need ~60 trading days → ~Aug 2026).
A clean data-driven floor calibration is therefore not yet possible and is deferred to
the decision ledger.

## 7. Decision — emergency reversible rollback (NOT the formal ~60d revert)

**Set `demean_cross_sectional` to OFF now**, as an **emergency operator-authorized,
reversible config rollback** prompted by **new fresh-feed evidence** (the first fresh /
PIT-valid day, 2026-06-29):
- it returns admission to the **known-prior trading config** (the pre-2026-06-24 state,
  `raw mu >= 0.03`);
- it is low-risk and trivially reversible (one boolean; no artifact/calibrator/pin
  change).

**This is NOT the monitored exception's formal revert.** The monitored exception
defines its revert criteria at the ~60d review as
`dropped_by_demean_mean_fwd > 0` OR `demean_minus_raw_mean_fwd <= 0`. Those are
**realized-return** metrics; no live `fwd_60d` has realized yet, so **none of the
formal revert criteria are evaluable today**. We therefore do **not** claim that
today's incident "triggers the exception's own revert clause." The formal ~60d metrics
remain the path to a **permanent** decision; today's change is an interim emergency
rollback on the admission/operational axis only.

**Alternative considered:** keep `demean` ON and lower `mu_floor` to a round-trip
transaction-cost hurdle (~0.005). **Rejected for now** because the exact hurdle value
cannot be validated until live forward returns realize (~Aug 2026), and reverting to
the known-prior config is the lower-risk move. We can revisit the absolute-floor
calibration (intercept-gating vs cost-hurdle) once clean data exists.

## 8. Operational guardrails

This change is justified on the **admission/operational** axis (testable now), with
outcome validation explicitly deferred. The guardrails:

- **Operational objective.** Avoid an accidental **total trading shutdown** (a
  zero-admission gate that silently halts all new buys) while keeping risk capped. The
  objective is NOT "get some buys" as a success criterion; it is "do not let a
  scale-mismatched gate shut the book down, without loosening any risk control."
- **Expected admission range.** Admission stays **small**. Upstream
  `RealizedVolGate` + `VetoWeakBuys` (rank floor = mean + 1σ) already cap candidates to
  roughly **0–10 names/day** *before* the conviction gate. Demean-OFF then admits only
  that small surviving set that also clears `raw mu >= 0.03` — on 2026-06-29 that is the
  6 names in §3. Turning demean off does **not** widen the candidate funnel; it only
  removes the relative-vs-absolute scale mismatch at the final gate.
- **Risk caps still in force (unchanged).** Every downstream risk control is untouched
  by this change: QP position and sector exposure limits, Kelly sizing (half-Kelly
  `fractional = 0.3`, `sigma_horizon_days = 60`), the shorting mandate (default-NO, ≤2
  concurrent), wash-sale and `RealizedVolGate` screens, and the `mu_floor = 0.03`
  absolute quality floor itself. Only the *demean* transform on the conviction quantity
  is removed; the floor and all sizing/exposure gates are unchanged.
- **Rollback trigger.** Revert the one boolean (`demean_cross_sectional: false → true`)
  if, after deploy, admissions or turnover spike abnormally relative to the ~0–10/day
  expectation, realized drawdown breaches risk limits, OR the formal ~60d demean revert
  metrics (`dropped_by_demean_mean_fwd > 0` / `demean_minus_raw_mean_fwd <= 0`) trip at
  the review.
- **ON-vs-OFF comparison.** The admission counterfactual of §3 (demean ON admits **0**,
  demean OFF admits **6** on `2026-06-29-live-5970796e`). The **full QP sizing /
  turnover / order replay is pending** (see §9) and is NOT asserted here.

## 9. Validation plan

- **Admission (done, this PR):** the exact-bundle ON-vs-OFF admission counterfactual in
  §3 (0 vs 6 on `2026-06-29-live-5970796e`).
- **Full QP/turnover replay (follow-up, NOT yet run):** replay the same stored bundle
  through QP sizing + turnover + downstream gates to quantify orders, position sizes and
  turnover under demean-OFF. Documented as a follow-up; no buys/orders/turnover are
  asserted until this runs.
- **Decision-ledger accumulation (dependency NOT yet met):** the live decision ledger is
  **renquant-pipeline PR #152**, which is **itself currently unwired** (no deployed
  producer). We do **NOT** claim ledger data "starts accumulating" — that begins only
  once the #152 producer wiring is deployed and proven. Until then there is no live
  `raw + mu + selected + realized-fwd` capture.
- **~Aug 2026 review:** once live `fwd_60d` has realized (~60 trading days after the
  2026-04-22 first clean OOS run) AND the ledger is wired/accumulating, revisit the
  absolute-floor calibration using genuinely out-of-sample forward returns (not
  look-ahead-contaminated sim IC). At that review, decide between: (a) keep raw
  `mu_floor = 0.03`; (b) lower the floor to a measured round-trip cost hurdle;
  (c) re-enable demean only if it demonstrably improves realized forward returns. This
  review is also where the **formal** monitored-exception revert metrics become
  evaluable.

## 10. Reversibility

Flip the one boolean back: `demean_cross_sectional: false → true`. No artifact,
calibrator, or pin changes are involved. Applies identically to active and golden
(pinned by `test_conviction_gate_demean_is_off_and_mu_floor_pinned`).
