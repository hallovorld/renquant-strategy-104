# Cash drag: raise slot counts (max_concurrent_positions, panel_buy_top_n)

**Date:** 2026-06-29
**Status:** PROPOSAL (awaiting Codex review) — NOT yet deployed
**Change (two integers only):**
- `max_concurrent_positions` (top-level): `8` → `12`
- `rotation.panel_buy_top_n`: `3` → `5`

Applied to BOTH `strategy_config.json` (active) and `strategy_config.golden.json`
(policy baseline) so active == golden, with an explicit pinning test
(`test_cash_drag_slot_counts_are_pinned_and_active_matches_golden`).

This raises **slot counts only**. Per-name risk, per-sector risk, and Kelly
aggression are deliberately left unchanged (see §3). It reduces cash drag; it
does **not** improve signal quality (see §5 caveat).

## 1. The measured cash drag

After the demean-revert (#34) restored buying earlier today, a real
`daily-full` run on the live book placed only two buys:

```
SOFI   $473
NEE    $354
------------
total  $827   of $8,730 buying power  (~9% of BP deployed THIS run)
```

The live book sits at roughly **46% deployed / ~54% cash**, holding 5-7
positions. That is a real, persistent cash-drag problem: a book that is
chronically half in cash forgoes roughly half the strategy's intended market
exposure.

These figures (`$827 / $8,730`, ~46% deployed, 5-7 positions) were measured
today, 2026-06-29, on the live book. They are a snapshot of one run / one book
state, not a distribution.

## 2. Two-cause diagnosis (it is NOT loose risk caps)

The per-name 12% concentration cap is **never the binding constraint** — the
book never approaches it. Cash drag comes from two slot limits compounded with
small position targets:

**Cause A — slot caps throttle the *count* of positions.**
- Top-level `max_concurrent_positions = 8`, with 5 names already held, leaves
  only **3 open slots**.
- `rotation.panel_buy_top_n = 3` independently caps new buys to **≤3 per run**.

Tonight 6 candidates survived the veto (FTNT / SOFI / NEE / BLK / AVGO / CVX).
FTNT was correlation-blocked. `panel_buy_top_n = 3` together with the 3 open
slots capped selection to **3 SELECTs** (SOFI / NEE / BLK), of which only **2
were sized** — BLK rounded down to 0 shares at ~$950/share against its small
target. So six viable candidates collapsed to two filled buys.

**Cause B — small Kelly targets from low model mu.**
The XGB model emits low expected returns (`mu ≈ 0.03–0.05`). Kelly sizing uses
`f* = mu / sigma^2` (mu and sigma horizon-matched at 60d), scaled by
`fractional = 0.30`. Low mu therefore produces **small ~3–5% per-name targets**.
Even a *full* 8-position book at those targets deploys only ~30–50% of capital —
nowhere near the per-name or per-sector caps.

A and B compound: few slots × small targets = a structurally under-deployed
book. The risk caps are slack, not tight; raising them would not help and would
relax risk we want to keep.

## 3. The change, and why slots (not Kelly)

| Key | Old | New | Touched? |
| --- | --- | --- | --- |
| `max_concurrent_positions` (top-level) | 8 | **12** | yes |
| `rotation.panel_buy_top_n` | 3 | **5** | yes |
| `ranking.kelly_sizing.fractional` | 0.30 | 0.30 | no |
| `ranking.kelly_sizing.max_concentration` | 0.12 | 0.12 | no |
| `position_sizing.max_position_pct` | 0.15 | 0.15 | no |
| `regime_params.BULL_CALM.max_position_pct` | 0.12 | 0.12 | no |
| `max_positions_per_sector` | 6 | 6 | no |
| `max_sector_weight_pct` | — | unchanged | no |
| `regime_params.CHOPPY.max_concurrent_positions` | 4 | 4 | no (regime override, distinct) |

Why raise slots and not Kelly:
- **Per-name risk is deliberately preserved.** Raising slot counts lets the book
  hold *more small* positions; it does not enlarge any single position. The 12%
  per-name and per-sector caps continue to bound concentration.
- **Kelly `fractional = 0.30` is the operator's deliberate setting.** It was
  retuned 0.5 → 0.3 alongside the 2026-06-11 sigma-horizon fix specifically to
  keep total deployment sane rather than pinning every name at the cap. Touching
  it would change per-name aggression, which is out of scope here and would
  re-open a settled decision.

So this addresses Cause A directly (more slots, more new buys per run) and lets
the existing small Kelly targets aggregate across a larger position count to
deploy more capital — without changing what any one position can be.

## 4. Expected effect (not a guarantee)

- The book can hold up to **12** small positions instead of 8, and admit up to
  **5** new buys per run instead of 3.
- With small (~3–5%) Kelly targets, ~12 positions can deploy on the order of
  ~36–60% of capital from sizing alone; combined with a deeper new-buy pipeline
  the book should drift from ~46% toward **~55–60% deployed** as candidates fill
  over successive runs.
- This is **not a guarantee.** Actual deployment depends on how many names clear
  the veto each run, correlation blocks, share-rounding at high prices, and the
  regime. On a thin candidate day it may barely move. The numbers are an
  *expected direction and rough magnitude*, not a committed target.

`12` and `5` are a **calibrated first pass for operator / Codex review**, not a
tuned optimum. They were chosen to give the book clear headroom over the current
holding count without lurching to a very different concentration profile; the
right values can be revisited once we observe realized deployment over a few
runs.

## 5. Honest caveat — this does not fix signal quality

More deployment means **more exposure to the model's current picks**, and the
model's ranking presently runs roughly **inverse to sell-side analyst upside**:
on recent runs the model tops names the street rates Hold (e.g. FTNT, SOFI) and
underweights names the street rates Strong Buy (e.g. BLK, AVGO). Reducing cash
drag therefore deploys capital *into a ranking we have independent reason to
distrust*.

This change is scoped to the **capital-deployment** problem only. It does not
claim to improve, and should not be read as improving, the *quality* of what
gets bought. The deeper lever — making the picks better — is orthogonal /
analyst-signal blending, tracked on the 105 line, and is explicitly out of scope
here. Approving this is a decision to accept more exposure to the current signal
in exchange for less idle cash; it is not a decision that the current signal is
good.

## 6. Reversibility

Fully reversible by reverting **two integers** (`12 → 8`, `5 → 3`) in both
config files. No artifact changes, no retrain, no schema change. The pinning
test will flag any silent drift in either direction.

## 7. Validation

- `tests/test_strategy_configs.py::test_cash_drag_slot_counts_are_pinned_and_active_matches_golden`
  pins `max_concurrent_positions == 12` and `panel_buy_top_n == 5`, asserts
  active == golden for both, and re-asserts the untouched risk knobs
  (`fractional 0.30`, `max_concentration 0.12`, BULL_CALM `max_position_pct
  0.12`, `max_positions_per_sector 6`) as a guard against accidental risk
  relaxation.
- The existing `test_active_and_golden_semantic_config_match` continues to pass
  (the new comment keys are `_`-prefixed and stripped as provenance).
- Full suite green (27 passed) — see the progress note for how it was run.

## 8. What is NOT in this change

- No change to any per-name or per-sector risk cap.
- No change to Kelly `fractional`, `max_concentration`, or `sigma_horizon_days`.
- No change to the conviction gate (`mu_floor 0.03`, `demean_cross_sectional`
  false from #34).
- No change to the scorer, artifacts, or any model.
- No deployment — this is a proposal PR for Codex review.
