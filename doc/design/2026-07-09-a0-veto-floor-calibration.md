# Design: A-0 VetoWeakBuys floor calibration for PatchTST

STATUS: design / RFC  
DATE: 2026-07-09  
PREREQ: RFC #421 (merged, orchestrator), RS-2 Lane A timing (orchestrator)

## 1. Problem

`VetoWeakBuysTask` uses an adaptive floor `max(0.20, mean + std_mult × std)` on the
cross-sectional calibrated `rank_score` distribution. With `std_mult=1.0`, the floor
sits at ~0.54-0.58 daily and kills **80% of scored candidates** (66/83 on 07-02,
55/73 on 06-24, 58/76 on 06-25).

This threshold was calibrated for XGB-era scores with wider dispersion. PatchTST's
calibrated rank_score distribution clusters in [0.45, 0.65] — much narrower. The 1σ
threshold mechanically filters the MIDDLE of the distribution, not just noise.

## 2. Evidence

### 2.1 Funnel data (11 trading days, 06-23 → 07-09)

| Date | Scored | Post-veto | Kill rate | Floor |
|---|---|---|---|---|
| 06-23 | 81 | 18 | 78% | 0.557 |
| 06-24 | 73 | 18 | 75% | 0.543 |
| 06-25 | 76 | 18 | 76% | 0.539 |
| 06-26 | 79 | 14 | 82% | 0.581 |
| 06-29 | 43 | 6 | 86% | 0.587 |
| 07-02 | 83 | 17 | 80% | 0.575 |
| 07-07 | 33 | 5 | 85% | 0.554 |
| **avg** | **67** | **14** | **80%** | **0.562** |

### 2.2 Score distribution (PatchTST vs gate)

PatchTST calibrated rank_score on 07-02 (83 candidates):
- Mean: ~0.50
- Std: ~0.07
- Floor at mean+1σ: 0.575
- Floor at mean+0.5σ: ~0.535
- Candidates above 0.575: 17 (20%)
- Candidates above 0.535: ~33 (40%)

### 2.3 Theory

The adaptive floor is a cross-sectional quality filter. The underlying assumption is
that scores below mean+kσ are noise. For a normally distributed signal:
- k=1.0: admits top 16% (one-tailed)
- k=0.5: admits top 31%

With PatchTST's compressed distribution, the ABSOLUTE quality represented by 0.55 is
different from what 0.55 meant under XGB. The calibrator maps these to ERs; a
rank_score of 0.55 maps to ER≈+3% (positive, meaningful). The floor is rejecting
candidates with positive expected returns.

Grinold & Kahn (2000) recommend that portfolio optimization, not pre-filtering, should
handle the quality/quantity tradeoff. Aggressive pre-filtering before Kelly sizing
compounds with whole-share quantization to strand cash.

## 3. Proposed change

```
ranking.panel_scoring.buy_floor_std_mult: 1.0 → 0.5
```

Expected effect: candidate survival rate ~20% → ~40% (an additional ~15-20
candidates per day reaching Kelly sizing).

No other parameter changes. One change at a time per RFC #421 / RS-2.

## 4. Preregistered shadow protocol

Per RS-2's one-change-at-a-time requirement:

### 4.1 Design

- **Baseline**: `buy_floor_std_mult=1.0` (current production)
- **Treatment**: `buy_floor_std_mult=0.5`
- **Frozen session set**: 10 sessions from the score_db (dates to be frozen in the
  shadow-sweep PR BEFORE data is inspected)
- **All other parameters held constant** (A-0b, A-2, A-3 at production values)

### 4.2 Estimands

Primary:
- Deployed fraction change (cash % of equity)
- Number of candidates reaching Kelly sizing

Secondary (non-degradation gates):
- Turnover (round-trip count within tolerance of baseline)
- Single-name concentration (must not exceed 12% cap)
- Sector concentration (must not exceed sector cap)
- Max drawdown (no worse than baseline window)

### 4.3 Decision rule

ENABLE if:
- Deployed fraction increases by ≥5pp (material cash drag reduction)
- ALL non-degradation gates pass
- No single session shows concentration violation

REJECT if:
- Any non-degradation gate breached
- Deployed fraction increase < 5pp (not worth the complexity)

### 4.4 Rollback

Single config value revert (`buy_floor_std_mult: 0.5 → 1.0`). No state migration.

## 5. Non-goals

- This does NOT change the conviction gate (mu_floor), Kelly sizing, rotation
  threshold, or any other parameter
- This does NOT bypass correlation, sector, or risk gates
- This does NOT authorize A-0b, A-2, or A-3 simultaneously
