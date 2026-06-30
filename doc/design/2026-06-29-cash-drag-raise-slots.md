# Cash drag analysis — slot raise is a WEAK fix; fractional shares is the real lever

**Date:** 2026-06-29
**Status:** ANALYSIS RECORD — proposal-only. Active/golden config is UNCHANGED
(stays at production `8 / 3`); this PR merges as the cash-drag decision record,
**not** as a config change.
**Outcome:** Do **NOT** raise slot counts in isolation. The real lever is
**FRACTIONAL SHARES**, optionally plus a min-conviction floor. Slot count is
secondary.

## TL;DR

A real `daily-full` run on the live book today deployed only **$827 of $8,730**
buying power (~46% deployed / ~54% cash). A staged slot raise `8/3 → 10/4` was
proposed as the fix. We then ran a **readonly 8/3-vs-10/4 replay today on the
live book** (no real orders). The result: **10/4 deploys only ~$427 more**, and
that marginal deployment is a low-conviction name (ZM) plus CVX — while the
genuinely better high-price names (**AVGO, BLK, GS**) were *selected but skipped
by whole-share rounding* because their Kelly targets (~$400, ~4%) are smaller
than one share. So raising slots barely moves cash drag on this account size and
admits a marginal name (ZM, conv 0.36), exactly the concern Codex raised. The
binding constraint is **whole-share rounding on high-priced names**, not slot
count. The fix that actually unlocks the good names is **fractional shares**.

## What changed after Codex review (CHANGES_REQUESTED on PR #35)

Codex's two CHANGES_REQUESTED reviews are accepted. The second review offered two
clean shapes: (1) **proposal-only** — revert active/golden, keep the docs and
criteria; or (2) **deploy-candidate** — keep 10/4 and attach a real readonly
replay. We took **option 1 (proposal-only)** — and crucially, the readonly replay
we ran to support option 2 *changed the conclusion*: it showed the slot-raise is a
weak fix and surfaced the real bottleneck (whole-share rounding), so changing
active production policy is not warranted. Active/golden are reverted to the
production `8/3`; the config diff vs `main` is now **empty**. This document is the
durable analysis record and the pointer to the real lever.

## 1. The measured cash drag

After the demean-revert (#34) restored buying earlier today, a real `daily-full`
run on the live book placed only two sized buys:

```
SOFI   $473
NEE    $354
------------
total  $827   of $8,730 buying power  (~9% of BP deployed THIS run)
```

The live book sits at roughly **46% deployed / ~54% cash**, holding 5-7
positions. That is a real, persistent cash-drag problem: a book that is
chronically half in cash forgoes roughly half the strategy's intended market
exposure. These figures (`$827 / $8,730`, ~46% deployed, 5-7 positions) were
measured today, 2026-06-29, on the live book — a snapshot of one run / one book
state, not a distribution.

## 2. The readonly 8/3 vs 10/4 replay (run today, no real orders)

**Provenance:** run today on the live book as a **readonly replay** through the
order-generation path — same candidates, prices, and holdings — under both the
production `8/3` and the proposed `10/4` configs. No real orders were placed.

### Result: 10/4 deploys only ~$427 more, and it is the WRONG ~$427

| Config | marginal new deployment | what filled |
| --- | --- | --- |
| **8/3** (production) | — | the existing $827 book |
| **10/4** (proposed) | **+~$427** | **CVX ~$169 + ZM ~$258** |

The extra ~$427 from raising slots is **CVX $169 + ZM $258** — and ZM is a
**low-conviction marginal name (conv = 0.36)**. So the slot raise (a) barely
dents the ~$3,900 of idle cash, and (b) the marginal slot it opens is filled by a
weak name. This is exactly Codex's concern that raising slots "admits lower-quality
marginal names" — **confirmed by the real replay.**

### The good high-price names were SELECTED but SKIPPED by whole-share rounding

The names the strategy actually *wanted* — the high-conviction, street-better
ones — were selected by the ranking but **bought 0 shares** because their Kelly
dollar target is smaller than a single share:

| Name | Kelly $ target | ~% of book | share price | shares bought |
| --- | --- | --- | --- | --- |
| **AVGO** | ~$400 | ~4% | ~$373 | would be ~1 sh, but target < 1 full position |
| **BLK** | ~$400 | ~4% | ~$950 | **0** (target < 1 share) |
| **GS** | ~$400 | ~4% | ~$1,022 | **0** (target < 1 share) |

Each of AVGO / BLK / GS had a Kelly target around **$400 (~4% of the book)** that
is **smaller than one whole share** of the respective stock, so whole-share
rounding floored them to **0 shares**. These are precisely the names that would
*improve* the book (high-priced, often higher sell-side-rated), and they are
locked out by **rounding, not by slots**. Raising the slot count does nothing for
them — the new slots get filled by cheaper, lower-conviction names instead.

### Why this overturns the slot-raise hypothesis

The earlier (pre-replay) single-day **derived** counterfactual suggested 10/4 would
add AVGO (a Strong Buy) and deploy ~$1,227. The **actual readonly replay**
contradicts that: AVGO does not fill (rounding), the marginal deployment is only
~$427, and the names that *do* fill are CVX + a low-conviction ZM. The derived
arithmetic missed the whole-share-rounding interaction on the high-price names —
which is exactly the kind of interaction Codex warned a derived (non-execution)
counterfactual could miss. The real bottleneck on this account size is
**whole-share rounding of small Kelly targets on high-priced stocks**, and slot
count is secondary.

## 3. Conclusion — the real lever is fractional shares

**Raising slot counts is a WEAK cash-drag fix on this account size.** With ~$8.7k
of buying power and Kelly targets of ~$400 (~4%) per name, any stock priced above
~$200-400 rounds to 0 or 1 share, so the strategy cannot express its intended
small position in the very names (AVGO/BLK/GS) that would most improve the book.
More slots just admit cheaper, often lower-conviction names (CVX, ZM).

The lever that actually unblocks the good names:

1. **FRACTIONAL SHARES (primary).** Fractional / notional order sizing lets the
   high-price, high-conviction names (AVGO, BLK, GS) get bought at their small
   ~$400 targets instead of rounding to 0. This directly attacks the binding
   constraint the replay exposed, and it deploys cash into the *better* names
   rather than into marginal ones. (Requires broker/adapter support for
   fractional or notional orders; that is the real engineering task.)
2. **Min-conviction floor (optional complement).** A minimum-conviction gate on
   new admits so that ZM-class names (conv ~0.36) don't fill slots just because
   they happen to be cheap enough to round to a whole share. This addresses the
   "admits lower-quality marginal names" failure directly.
3. **Slot count is SECONDARY.** With fractional shares in place, the existing 8/3
   slots may already deploy materially more cash (because the good names finally
   fill). Re-measure slot pressure *after* fractional shares; do not raise slots
   in isolation.

**Recommendation: do NOT raise slots in isolation. Pursue fractional shares
(plus optionally a min-conviction floor). This PR merges as the analysis record
only; the active/golden config is unchanged.**

## 4. Why not just turn the `qp_cash_drag_lambda` pressure term back on

For completeness / context (this remains the right call):

`configs/strategy_config.json` carries a note around `qp_cash_drag_lambda = 0`:
cash-deployment pressure was a knob that let marginal candidates become trades,
and it was **disabled** until there is WF evidence that benchmark-relative alpha
survives the strict admission gate. Raising slot counts is in the **same family**
— a cash-deployment-pressure knob by a different mechanism. It raises total
exposure to the current ranking, which is independently suspect (it runs roughly
inverse to sell-side upside). The replay reinforces this: the cash it deploys
goes into CVX/ZM, not the better names. So neither re-enabling the lambda nor
raising slots is the right move; fractional shares deploys cash into the *good*
names without manufacturing trades from cash-drag pressure on a distrusted
ranking.

## 5. Rollback / promote criteria (kept as context for any future slot change)

These were pre-registered for the slot-raise experiment. They are **retained here
as the bar any future slot change must clear**, but they are NOT active criteria
for this PR (which makes no config change). If a slot raise is ever revisited
*after* fractional shares is in place:

### REVERT a slot raise if ANY of:

- **Deployment doesn't materially rise.** Median deployed-% over the first
  **N = 10 fresh-feed days** does not rise by at least **+5 percentage points**
  vs the ~46% baseline.
- **The marginal (slot-4+) names underperform the first-3 names** by more than
  **−2.0 percentage points** benchmark-relative over the ledger horizon.
- **Rounding / slippage waste is excessive.** Realized slippage + share-rounding
  waste on marginal buys exceeds **30 bps** of marginal deployed dollars, OR more
  than **40%** of marginal admits round to 0 shares. *(The replay already shows
  this condition tripping today: AVGO/BLK/GS round to 0 — which is exactly why the
  slot raise fails and fractional shares is needed first.)*
- **Book risk breaches a bound.** Gross exposure exceeds **75%** of buying power,
  OR book drawdown exceeds **−8%**, OR any per-name/per-sector cap is breached.

### PROMOTE a slot raise ONLY if:

- After fractional shares is live, the decision-ledger (once it has enough realized
  fwd returns, ~Aug 2026 for 60d) shows the **slot-4+ admitted names are not
  net-negative benchmark-relative** AND none of the REVERT conditions trip.

## 6. Honest caveat — this does not fix signal quality

More deployment means more exposure to the model's current picks, and the model's
ranking presently runs roughly **inverse to sell-side analyst upside** (it tops
names the street rates Hold and underweights Strong Buys). Fractional shares lets
us deploy into the *better-rated* high-price names (AVGO/BLK/GS), which is a
modest improvement on the *capital-deployment* axis only. It does **not** fix the
ranking. The deeper lever — making the picks better — is orthogonal / analyst-
signal blending, tracked on the 105 line, and is out of scope here.

## 7. Validation status

- The decision-ledger is too short for multi-day validation — clean PIT-fresh live
  data only began **2026-06-29**. There is no multi-day fresh-feed distribution
  yet.
- The §2 readonly replay was run **today** on the live book through the order path
  (readonly, no real orders); it is execution-faithful for the 2026-06-29 book and
  is the evidence that slot-raise is weak and fractional shares is the lever. It is
  one date, not a distribution.
- This PR makes **no config change** and therefore needs no live validation to
  merge — it is the analysis record. The next engineering step is fractional /
  notional order support.

## 8. What this PR does and does NOT do

- **Does NOT** change `max_concurrent_positions` or `rotation.panel_buy_top_n` —
  both stay at the production **8 / 3** in active AND golden. Config diff vs `main`
  is empty.
- **Does NOT** change any per-name or per-sector risk cap, Kelly `fractional`
  (0.30), the conviction gate, the scorer, artifacts, or `qp_cash_drag_lambda`
  (stays 0 / disabled).
- **DOES** record the measured cash drag, the readonly replay finding, and the
  recommendation to pursue **fractional shares** (plus optionally a min-conviction
  floor) as the real lever, with slot count secondary.

## 9. Validation (tests)

- `tests/test_strategy_configs.py::test_cash_drag_slot_counts_stay_at_production_8_3`
  pins `max_concurrent_positions == 8` and `panel_buy_top_n == 3` in BOTH active
  and golden (so this analysis stays proposal-only and cannot silently raise live
  policy), asserts active == golden, and re-asserts the untouched risk knobs
  (`fractional 0.30`, `max_concentration 0.12`, BULL_CALM `max_position_pct 0.12`,
  `max_positions_per_sector 6`).
- The existing `test_active_and_golden_semantic_config_match` continues to pass.
- Full suite green — see the progress note for how it was run.
