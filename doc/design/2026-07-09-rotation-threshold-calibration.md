# Design: P0 rotation threshold calibration

STATUS: design / RFC
DATE: 2026-07-09
PREREQ: RFC #421 (merged, orchestrator), RS-2 Lane A timing

## 1. Problem

`min_expected_advantage_pct=0.06` makes rotation **structurally impossible** for the
XGB panel scorer. Production has never fired a rotation in the study window (06-23 to
07-07, 7 trading days with candidates).

The rotation check is:

```
net_adv = cand_er - held_er - tax_drag(pnl, hold_days) - transaction_cost_pct
rotation fires iff net_adv >= min_expected_advantage_pct
```

The XGB calibrated ER range is [0, 0.062]. Maximum possible raw advantage
(max_cand_er − min_held_er) ≈ 0.05. This is below the 0.06 threshold **by
construction** — no candidate can ever produce a 6% net advantage.

The code default is `0.03` (rotation.py:447). Production overrides to `0.06` — a
value 2× the designed default, with no documented calibration rationale.

## 2. Evidence

### 2.1 Rotation tree: 7 days, 0 rotations

| Date | Best candidate | Best held to rotate | raw_adv | tax | net_adv | Blocked by |
|---|---|---|---|---|---|---|
| 06-23 | PANW (0.0624) | MU (0.0542) | +0.008 | 0.544 | −0.536 | tax (MU +109%) |
| 06-24 | CAT (0.0358) | AMZN (0.0341) | +0.002 | 0.002 | +0.000 | tiny advantage |
| 06-26 | FTNT (0.0505) | AMZN (0.0078) | +0.043 | 0.000 | **+0.043** | threshold only |
| 06-29 | FTNT (0.0515) | AMZN (0.0222) | +0.029 | 0.017 | +0.013 | threshold + tax |
| 07-02 | FTNT (0.0511) | CSCO (0.0225) | +0.029 | 0.000 | **+0.029** | threshold only |
| 07-07 | ZM (0.0336) | AMZN (0.0102) | +0.024 | 0.029 | −0.006 | tax (AMZN +5.8%) |

**Cases that would fire at threshold=0.02:**
- 06-26: FTNT→AMZN (net_adv=0.043) — BUT killed downstream by correlation guard
  (corr with CRWD = 0.71)
- 07-02: FTNT→CSCO (net_adv=0.029) — **survives all downstream guards**

**Cases that would NOT fire even at threshold=0:**
- 06-23, 07-07: tax drag from profitable positions dominates
- 06-24: ER difference too small (model sees both similarly)

### 2.2 Mechanism: why rotation ≠ cash drag fix

Rotation is sell-one-buy-one. Net cash change ≈ 0 (position-size delta only).
This does NOT directly reduce the 60-70% cash drag.

What rotation fixes: **portfolio QUALITY** — replace a losing/low-conviction
name with a higher-scoring candidate. The cash drag fix requires more
positions and/or bigger positions (see §5 for sizing analysis).

### 2.3 Theory

Perold (1988) optimal no-trade band: width ∝ √(transaction_cost × holding_period).
With `transaction_cost_pct=0`, the only cost is tax. Tax is already deducted in
`net_adv`. The threshold should represent estimation uncertainty only.

The XGB calibrated ER has standard error ≈ 0.015-0.020 (based on cross-sectional
std of ~0.07 in rank_score → ~0.02 in ER terms through the calibrator). A threshold
of 0.02 represents roughly 1× the estimation uncertainty — a defensible hurdle.

## 3. Proposed change

```
rotation.min_expected_advantage_pct: 0.06 → 0.02
```

Expected effect: unblocks rotations from loss/flat positions into stronger
candidates. Does NOT increase rotations from profitable positions (tax drag
dominates regardless). Does NOT directly reduce cash drag.

## 4. Preregistered shadow protocol

### 4.1 Design

- **Baseline**: `min_expected_advantage_pct=0.06` (current production)
- **Treatment**: `min_expected_advantage_pct=0.02`
- **Frozen session set**: 10 sessions from score_db (dates frozen before data
  inspection in the shadow-sweep PR)
- **All other parameters held constant**

### 4.2 Estimands

Primary:
- Number of rotation pairs proposed (currently 0)
- Quality of proposed rotations: average net_adv of fired rotations

Secondary (non-degradation):
- Turnover (excess round-trips within tolerance)
- Single-name concentration (must not exceed 12% cap)
- Win rate of rotation exits (exit names that subsequently dropped vs held)

### 4.3 Decision rule

ENABLE if:
- ≥1 rotation fires in the shadow window (currently 0; any increase is material)
- Average net_adv of fired rotations > 0 (rotations are expected-positive)
- Turnover increase < 2× baseline (not generating churn)

REJECT if:
- Turnover increase ≥ 2× baseline
- Rotations show negative net_adv on average (calibration error)

### 4.4 Rollback

Single config value revert. No state migration.

## 5. Cash drag: the real lever is SIZING (not rotation)

Current deployment on 07-02: 5 positions × ~5% avg = ~25-35% deployed, 65% cash.

Even if rotation fires perfectly, it doesn't create NEW positions — it replaces
held ones. To deploy more cash, the system needs to either:

**A. Size up existing/new positions (BIGGEST IMPACT)**
- `kelly_sizing.fractional: 0.5 → 0.7-0.8` — positions from 2-7% to 3-8%
- `sigma_sizing.floor: 0.3 → 0.5` — less conviction compression
- Risk: higher concentration, but at $10.7k, a -20% move on a 10% position =
  -$214 (manageable)

**B. Add more positions (MODERATE IMPACT)**
- Lower veto floor (currently kills 80%) — DEFERRED per operator feedback
- Raise `panel_buy_top_n` for more initiations per day

**C. One-share floor (TARGETED)**
- Minimum 1 share for any Kelly-positive candidate — unblocks BLK ($995), AVGO ($360)

**Recommended P2 priority**: analyze Kelly fractional + sigma_sizing floor impact
in a separate design PR. The user's insight that "concentrate in the best names"
(bigger positions in top candidates) is the right framing for a $10.7k account
with weak IC.

## 6. Non-goals

- This PR does NOT change Kelly sizing, veto floor, or any other parameter
- This does NOT claim to solve cash drag — it fixes a single mis-calibration
- Sizing analysis (§5) is scoped to a separate design PR (P2)
