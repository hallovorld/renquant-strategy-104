# Cash drag: staged slot raise (max_concurrent_positions, panel_buy_top_n)

**Date:** 2026-06-29
**Status:** PROPOSAL (Codex review revision) — NOT yet deployed
**Change (two integers only) — STAGED first step:**
- `max_concurrent_positions` (top-level): `8` → `10`  (proposed 12, downgraded to a staged 10)
- `rotation.panel_buy_top_n`: `3` → `4`  (proposed 5, downgraded to a staged 4)

Applied to BOTH `strategy_config.json` (active) and `strategy_config.golden.json`
(policy baseline) so active == golden, with an explicit pinning test
(`test_cash_drag_slot_counts_are_pinned_and_active_matches_golden`).

This raises **slot counts only**, and only by a **staged** first step. Per-name
risk, per-sector risk, and Kelly aggression are deliberately left unchanged (see
§3). It begins to reduce cash drag; it does **not** improve signal quality (see §6
caveat).

### What changed after Codex review (CHANGES_REQUESTED on PR #35)

Codex's critique is valid and accepted. The original proposal jumped to 12/5 on
one-snapshot arithmetic. This revision:

- **Downgrades 12/5 → a STAGED 10/4** — the first step, not a permanent jump
  (Codex: "the right answer may be staged admission, not a permanent jump to
  12/5").
- Adds a **single-day counterfactual** of 8/3 vs 10/4 vs 12/5 (§2), labelled
  DERIVED from stored scores + selection logic (not a fresh execution).
- Addresses the **`qp_cash_drag_lambda = 0` conflict head-on** (§4): raising
  slots IS a cash-deployment-pressure knob in the same family, and total exposure
  to the (suspect) ranking rises. "Per-name risk unchanged" is explicitly NOT
  claimed to be sufficient.
- Pre-registers **rollback / promote criteria** with first-pass thresholds (§5).
- States the **honest validation status** plainly (§7): the ledger is too short
  for multi-day validation; this is a staged, reversible step, not a validated
  optimum.

## 1. The measured cash drag

After the demean-revert (#34) restored buying earlier today, a real
`daily-full` run on the live book placed only two sized buys:

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

## 2. Single-day counterfactual: 8/3 vs 10/4 vs 12/5

**Provenance / honesty label:** the table below is **DERIVED** from the stored
2026-06-29 live candidate scores (run `2026-06-29-live-5970796e`) plus the
documented selection logic (top-`n`-by-rank into open slots, then Kelly sizing
and share-rounding). It is **NOT a fresh execution** and **NOT a full
readonly QP replay**; a live readonly replay under each config is the proper
confirmation and is a pending follow-up. Treat the dollar figures as the
arithmetic of the selection layer, not realized fills.

Setup on 2026-06-29: 6 candidates survived the veto
(FTNT / SOFI / NEE / BLK / AVGO / CVX); FTNT was correlation-blocked, leaving 5
admissible (SOFI / NEE / BLK / AVGO / CVX, in rank order). The live book held 5
names, so the open-slot count is `max_concurrent_positions − 5`.

| Config | open slots | top_n | selected (by rank) | sized buys | derived deployed $ |
| --- | --- | --- | --- | --- | --- |
| **8/3** (current) | 3 | 3 | SOFI, NEE, BLK | SOFI $473 + NEE $354 (BLK → 0 sh) | **~$827** |
| **10/4** (this PR) | 5 | 4 | SOFI, NEE, BLK, **AVGO** | SOFI $473 + NEE $354 + AVGO ~$400 (BLK → 0 sh) | **~$1,227** |
| **12/5** (original) | 7 | 5 | SOFI, NEE, BLK, AVGO, **CVX** | adds CVX on top of the 10/4 set | > $1,227 |

Notes:
- At **8/3**, the binding cap was both the 3 open slots and `top_n = 3`; AVGO hit
  "slots full" and never got a slot. BLK rounded to **0 shares** (~$950/share vs
  a small ~$400 target), so only SOFI + NEE actually sized → **~$827**.
- At **10/4**, the extra slot + `top_n = 4` admit exactly one more name, **AVGO**
  (the #4 by rank). BLK still rounds to 0 (the rounding problem is independent of
  slots). So 10/4 ≈ SOFI + NEE + AVGO ≈ **~$1,227**.
- At **12/5** it would further add **CVX** (#5 by rank).

### The marginal slots admit street-BETTER names, not junk

This is the direct answer to Codex's concern that more slots "admit lower-quality
marginal names." On this date the opposite is true — the names the extra slots
admit are **higher sell-side-rated** than the names 8/3 already buys:

| Name | admitted at | sell-side rating | approx. upside to target |
| --- | --- | --- | --- |
| SOFI | 8/3 (already bought) | **Hold** | — |
| NEE | 8/3 (already bought) | Buy | modest |
| AVGO | **10/4** (new) | **Strong Buy** | ~+35–40% |
| CVX | 12/5 (new) | Buy | ~+13% |

The 8/3 book already buys SOFI, which the street rates **Hold**. The marginal
slot at 10/4 admits **AVGO** — a sell-side **Strong Buy** with the largest
upside-to-target in the set. So on this one date the extra slots improve, not
degrade, the street-rating quality of the basket.

**Keep this honest:** this is the **analyst cross-check**, not realized P&L. It
shows the marginal admits are not junk on this date; it does NOT prove they will
outperform, and a single date is not a distribution. The model's own ranking runs
roughly inverse to these street ratings (it tops SOFI/FTNT), which is exactly why
deploying more into the model ranking is a caveat (§6), not a free win.

## 3. The change, and why slots (not Kelly)

| Key | Old | New | Touched? |
| --- | --- | --- | --- |
| `max_concurrent_positions` (top-level) | 8 | **10** | yes |
| `rotation.panel_buy_top_n` | 3 | **4** | yes |
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
  per-name and per-sector caps continue to bound concentration. (But see §4 —
  preserving per-name risk is NOT by itself a sufficient safety argument.)
- **Kelly `fractional = 0.30` is the operator's deliberate setting.** It was
  retuned 0.5 → 0.3 alongside the 2026-06-11 sigma-horizon fix specifically to
  keep total deployment sane rather than pinning every name at the cap. Touching
  it would change per-name aggression, which is out of scope here.

So this addresses the slot bottleneck directly (more slots, more new buys per
run) and lets the existing small Kelly targets aggregate across a slightly larger
position count — without changing what any one position can be.

## 4. Conflict with the disabled `qp_cash_drag_lambda = 0` safeguard

Codex is right to flag this, and it is acknowledged head-on.

`configs/strategy_config.json` carries a note around `qp_cash_drag_lambda = 0`:
cash-deployment pressure was previously a knob that let marginal candidates become
trades, and it was **disabled** until there is WF evidence that benchmark-relative
alpha survives the strict admission gate.

**Raising slot counts is in the same family.** It is a cash-deployment-pressure
knob by a different mechanism: it increases the *total exposure to the current
ranking*, and this PR itself argues (§6) that the current ranking is independently
suspect (it runs roughly inverse to sell-side upside). "Per-name risk is
unchanged" is therefore **NOT** a sufficient safety argument on its own — the
aggregate book-level exposure to a distrusted signal rises even though no single
position gets bigger. We do not claim otherwise.

Why the staged step is nonetheless acceptable as a *reversible experiment* (not a
validated promotion):

- **Staged small.** 10/4, not 12/5 — one extra held slot and one extra new buy
  per run. On 2026-06-29 the marginal admit is exactly one name (AVGO).
- **Every strict admission gate is UNCHANGED and still binding.** Slots only
  control *how many* of the already-admitted names get a seat; they do not relax
  any quality gate. Still in force and unchanged: the WF gate, the conviction
  `mu_floor` (0.03), the rank veto (mean + 1σ), correlation block, sector caps,
  min-edge, wash-sale / earnings windows, and share-rounding. The marginal name
  must already have cleared all of these.
- **Hard rollback** is pre-registered (§5) and the change is two integers.

This is the difference between re-enabling a *pressure term that manufactures
trades from cash drag* (the lambda) and *admitting one more already-gate-cleared
name per run* (the staged slot raise). Both raise deployment; the staged slot
raise does so only among names that already passed every quality gate, and is
reversible with a hard rollback. It is still an experiment on a suspect ranking,
to be validated by the ledger, not a validated promotion.

## 5. Rollback / promote criteria (pre-registered)

These are **first-pass thresholds**, set before deployment, to be refined once the
decision-ledger accrues. They are intentionally conservative.

### REVERT 10/4 → 8/3 if ANY of:

- **Deployment doesn't materially rise.** Median deployed-% over the first
  **N = 10 fresh-feed days** does not rise by at least **+5 percentage points**
  vs the pre-change ~46% baseline (i.e. stays below ~51%). *(first-pass)*
- **The marginal (slot-4+) names underperform the first-3 names.** Over the
  available ledger horizon, the benchmark-relative return of names admitted *only*
  because of the extra slot (rank ≥ 4) trails the first-3 names by more than
  **−2.0 percentage points** (benchmark-relative, equal-weight, on whatever
  realized horizon the ledger supports). *(first-pass)*
- **Rounding / slippage waste is excessive.** Realized slippage + share-rounding
  waste on the marginal buys exceeds **30 bps** of the marginal deployed dollars,
  OR more than **40%** of marginal admits round to 0 shares (i.e. the extra slot
  buys nothing useful). *(first-pass)*
- **Book risk breaches a bound.** Gross exposure exceeds **75%** of buying power,
  OR book drawdown over the observation window exceeds **−8%**, OR any
  per-name/per-sector cap is breached (which would itself be a separate bug).
  *(first-pass)*

### PROMOTE 10/4 → 12/5 ONLY if:

- The decision-ledger (once it has enough realized fwd returns, ~Aug 2026 for
  60d) shows the **slot-4+ admitted names are not net-negative benchmark-relative**
  — i.e. their mean benchmark-relative realized return over the ledger is **≥ 0**
  and not statistically worse than the first-3 names — AND none of the REVERT
  conditions above are tripping. Absent that evidence, 10/4 is the ceiling.

These are deployment-direction and quality guardrails, not just a deployment
target — directly answering Codex point 4 (deployment target alone is
insufficient; include marginal-candidate quality, slippage/rounding, drawdown,
and first-3-vs-rest underperformance).

## 6. Honest caveat — this does not fix signal quality

More deployment means **more exposure to the model's current picks**, and the
model's ranking presently runs roughly **inverse to sell-side analyst upside**:
on recent runs the model tops names the street rates Hold (e.g. FTNT, SOFI) and
underweights names the street rates Strong Buy (e.g. BLK, AVGO). Reducing cash
drag therefore deploys capital *into a ranking we have independent reason to
distrust*.

The §2 cross-check shows that on *this* date the marginal slot happens to admit a
street-Strong-Buy (AVGO), which is reassuring — but that is one date, and it does
not change the structural point: the model ranking itself is suspect. This change
is scoped to the **capital-deployment** problem only. The deeper lever — making
the picks better — is orthogonal / analyst-signal blending, tracked on the 105
line, and is explicitly out of scope here. Approving this is a decision to accept
*slightly* more exposure to the current signal in exchange for less idle cash,
under a hard rollback; it is not a decision that the current signal is good.

## 7. Honest validation status

Stated plainly:

- **The decision-ledger is too short for multi-day validation.** Clean,
  PIT-fresh live data only began **2026-06-29** (the fundamentals feed first
  became PIT-fresh that day). There is no multi-day fresh-feed distribution yet.
- **This is a STAGED, reversible first step**, to be validated via the ledger as
  it accrues (~Aug 2026 for a 60d realized horizon), **NOT a validated optimum**.
  The 10/4 numbers are a first step chosen for a small, reversible move, not a
  tuned result.
- **This does NOT fix signal quality.** The model ranking runs roughly inverse to
  sell-side; the orthogonal-signal blend is the 105 track and is out of scope.
- The §2 counterfactual is DERIVED from stored scores + selection logic, pending
  a live readonly replay; it is the selection-layer arithmetic, not realized P&L.

## 8. Reversibility

Fully reversible by reverting **two integers** (`10 → 8`, `4 → 3`) in both config
files. No artifact changes, no retrain, no schema change. The pinning test will
flag any silent drift in either direction.

## 9. Validation (tests)

- `tests/test_strategy_configs.py::test_cash_drag_slot_counts_are_pinned_and_active_matches_golden`
  pins `max_concurrent_positions == 10` and `panel_buy_top_n == 4`, asserts
  active == golden for both, and re-asserts the untouched risk knobs
  (`fractional 0.30`, `max_concentration 0.12`, BULL_CALM `max_position_pct
  0.12`, `max_positions_per_sector 6`) as a guard against accidental risk
  relaxation.
- The existing `test_active_and_golden_semantic_config_match` continues to pass
  (the new comment keys are `_`-prefixed and stripped as provenance).
- Full suite green (27 passed) — see the progress note for how it was run.

## 10. What is NOT in this change

- No change to any per-name or per-sector risk cap.
- No change to Kelly `fractional`, `max_concentration`, or `sigma_horizon_days`.
- No change to the conviction gate (`mu_floor 0.03`, `demean_cross_sectional`
  false from #34).
- No change to the scorer, artifacts, or any model.
- No change to `qp_cash_drag_lambda` (stays 0 / disabled).
- No deployment — this is a proposal PR for Codex review.
