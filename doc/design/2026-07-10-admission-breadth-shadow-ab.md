# Admission-breadth shadow A/B — preregistered protocol (buy_floor_std_mult 1.0 vs 0.5)

**Date**: 2026-07-10
**Status**: PREREGISTRATION (design doc + shadow-config flip in the same PR; zero
live behavior change)
**Successor to**: CLOSED strategy-104 PR #47 — every review blocker from that PR
is addressed explicitly in §8.
**Companion to**: orchestrator Deployment Governor RFC #443, D6 preregistered
replay protocol (`doc/design/2026-07-09-governor-prereg-replay-protocol.md`),
§2 Phase-2 amendment: veto-floor arms MOVED out of historical replay into this
live shadow A/B, because replay bars contain only post-admission survivors
(median candidate breadth 4) — pre-veto candidates are not in the sim DB, so a
veto {1.0σ, 0.5σ} arm cannot be replayed with existing data.

DISCIPLINE: every arm, estimand, gate, and tolerance below is FROZEN at PR
merge, BEFORE any evaluation session is run or inspected. Changes after merge
void the run and require a new protocol version with a fresh future window.

## 1. Decision context (hypothesis-generation evidence — labeled, not carried as predictions)

- **Production veto**: renquant-pipeline `VetoWeakBuys`, configured by
  `ranking.panel_scoring.buy_floor = "adaptive_mean_std"` with
  `buy_floor_std_mult = 1.0`: admission floor = `max(0.20, mean + 1.0·std)` on
  the calibrated cross-sectional `rank_score`, uncapped. On the 2026-06-23 →
  2026-07-09 production funnel it killed ~75-86% of scored candidates
  (11-session average ~80%). **This window is hypothesis-generation data and is
  EXCLUDED from evaluation** (§5).
- **Deployment identity**: `deployable ≤ breadth × cap`. The per-name cap is
  12% and the BULL_CALM ceiling is 0.95, so reaching the ceiling needs
  post-veto breadth ≥ 8 (8 × 12% = 96%). Live post-veto breadth has ranged
  5-17, frequently below 8 — admission breadth, not sizing, binds deployment.
- **The cap is the wrong lever** (orchestrator branch
  `design/deployment-governor-rfc`,
  `doc/research/evidence/cap_grid_tuning/results.md`, exploratory/tuning-subset,
  149 sessions): raising the per-name cap 12% → 25% bought +18pp mean
  deployment at **−8.2% net return** (vs +4.7% at cap 12 equal-weight), roughly
  doubled the single-name loss tail (p5 −0.97% → −1.98% of PV), and deepened
  MDD — dominated on every axis except raw deployment. Deployment stayed
  breadth-bound at every cap tested. Breadth is therefore the primary remaining
  lever, and the 12% cap stays UNCHANGED in this protocol.
- **Why live shadow, not replay**: per the D6 §2 Phase-2 amendment above —
  the sim DB has no pre-veto candidates, so admission treatments must run in
  the live shadow pipeline, which executes the FULL funnel (scoring → veto →
  conviction gate → QP → Kelly sizing → caps → whole-share sizing) on
  hard-isolated `alpaca_shadow` broker state (`live_state.alpaca_shadow.json`
  + `runs_alpaca_shadow.db`) and places zero live orders.

## 2. Hypothesis (hypothesis-level language, per the #47 review)

**H1**: relaxing the admission floor from `mean + 1.0σ` to `mean + 0.5σ`
increases post-veto breadth and end-of-chain deployed fraction **without
degrading portfolio quality** — specifically, the marginal entrants (names
admitted at 0.5σ but rejected at 1.0σ) earn forward returns that are
non-negative net of costs and not materially below the incumbent admitted set.

**0.5σ is a CANDIDATE TREATMENT, not a calibrated optimum.** It was chosen a
priori as the midpoint between the production floor (1.0σ) and no
dispersion-scaled floor (0σ, where only the `buy_floor_min = 0.20` fail-safe
remains). No expected candidate-count or deployment-lift numbers from the
motivation window are carried forward as predictions; H1 may be refuted, and a
REJECT verdict is a fully acceptable outcome of this protocol.

## 3. Arms

- **Baseline (control)**: production config `configs/strategy_config.json` —
  XGB primary, `adaptive_mean_std`, `buy_floor_std_mult = 1.0`. UNTOUCHED by
  this PR (golden also untouched).
- **Treatment**: shadow config `configs/strategy_config.shadow.json` —
  `buy_floor: "adaptive_quantile" → "adaptive_mean_std"` and
  `buy_floor_std_mult: 1 → 0.5`. Both keys must move together: under the
  previous `adaptive_quantile` mode the std-mult is dead config, and a
  dead-config flip would be a deployed-but-dark non-experiment.
- **Supersession**: this replaces the 2026-06-11 `adaptive_quantile(q=0.8)`
  shadow setting (false-BEAR audit P2), which never produced a recorded verdict
  memo. Its rationale (adaptive_mean_std shape-instability on Platt-compressed
  PatchTST scores) is preserved in git history and carried into §7
  limitations. `buy_floor_quantile: 0.8` is retained in the file but inert in
  `adaptive_mean_std` mode.

## 4. Estimands (preregistered; fixes #47 blocker 2)

**P1 — end-of-chain deployed fraction.**
1. Shadow vs production end-of-chain deployed fraction per session, paired by
   session date (delta series, mean and distribution).
2. **Attribution decomposition (required)**: within the shadow arm, each
   session's realized end-of-chain weight is split between *floor-incumbent*
   names (`rank_score ≥ mean + 1.0σ` of the shadow's own pre-veto
   cross-section) and *marginal entrants*
   (`mean + 0.5σ ≤ rank_score < mean + 1.0σ`). The marginal-entrant weight
   share is the treatment-attributable deployment lift. The raw shadow-vs-prod
   delta alone is NOT attributable to the floor (see the §7 confound register).

**P2 — quality of the marginal entrants (the estimand #47 lacked).**
Forward returns at 20d and 60d horizons (from the decision ledger / score_db,
as available; benchmark-relative vs SPY), of three same-session sets defined on
the pre-veto scored cross-section:
- (a) marginal entrants: admitted at 0.5σ, rejected at 1.0σ;
- (b) incumbent admits: `rank_score ≥ mean + 1.0σ`;
- (c) rejects: `rank_score < mean + 0.5σ` (sanity ordering check).

**Quality bar**: the marginal-entrant set's mean forward return must be
(i) ≥ 0 net of the 5 bps/side cost convention, and (ii) not significantly
below the incumbent set (paired per-session spread; HAC/Newey-West standard
errors, since 20d/60d forward-return overlap makes iid inference invalid).
"More deployed" with quality failing this bar = REJECT — a floor can raise
deployment by admitting lower-edge names and still make the portfolio worse;
this bar is exactly the check whose absence blocked #47.

**P3 — production counterfactual (scorer-transfer check).** Admission is a
deterministic function of the logged pre-veto scores, so the same marginal-set
construction (0.5σ vs 1.0σ) is ALSO computed counterfactually on the
PRODUCTION XGB cross-sections for the same future-only sessions — no config
change needed. The shadow instrument runs PatchTST; the enablement target is
prod XGB. A RECOMMEND-ENABLE verdict requires P2's quality bar to pass on
**both** the shadow instrument and the prod counterfactual.

## 5. Evaluation discipline (fixes #47 blocker 1)

- **Future-only**: ALL evaluation evidence comes from sessions strictly AFTER
  this PR merges. The 2026-06-23 → 2026-07-09 window that motivated 0.5σ is
  hypothesis-generation only and is excluded by construction — there is no
  overlap between the window that selected the parameter and the window that
  evaluates it.
- **Minimum 10 shadow sessions** before any verdict. Operational health
  monitoring (e.g. detecting a fail-closed contract error in the shadow run —
  a shadow no-trade can be a contract failure, not a decision) is permitted
  and logged; **estimand computation before session 10 voids the verdict**.
- **No mid-run tuning**: changing the treatment value, estimands, gates, or
  tolerances after any evaluation session has been inspected voids the run; a
  new value (e.g. 0.75σ) is a new protocol version on a fresh future window.
- **One extension allowed** (+10 sessions) if the 10-session evidence is
  directionally consistent but under-powered; the extension must be declared
  in the memo before inspecting any extension-window session.

## 6. Non-degradation gates (tolerances frozen now)

| Gate | Tolerance | Rationale |
|---|---|---|
| Per-name concentration | production 12% cap UNCHANGED; shadow book respects its configured caps (this PR changes no cap) | cap-grid evidence: cap-raising is dominated (−8.2% net for +18pp deployment, 2× loss tail) |
| Sector concentration | ≤ 35% per sector, max 6 names/sector | existing regime cap |
| Session turnover | shadow ≤ 2× the paired production session's turnover | churn control, mirrors D6 §4 |
| Drawdown | shadow book MDD over the evaluation window ≤ 0.30 | regime `drawdown_halt_pct` 0.35 with ≥ 5pp headroom, mirrors D6 §4 |

**Stop rule** (live-shadow venue, per D6 §5): immediate stop on any gate
breach; the breach is recorded and the verdict pathway is REJECT/REDESIGN.
No gate tolerance may be relaxed mid-run.

## 7. Confound register and limitations (stated up front, not discovered later)

1. **The shadow is not a single-delta clone of production.** Pre-existing
   deltas: scorer family (`hf_patchtst` vs `xgb`), Kelly `fractional` 0.5 vs
   0.3, Kelly `max_concentration` 0.35 vs 0.12, BULL_CALM `max_position_pct`
   0.15 vs 0.12, `one_share_floor_enabled` true vs false (2026-07-09 P1 shadow
   gate, running concurrently). These are deliberately NOT normalized here —
   flattening them would destroy the concurrently running one-share-floor
   RS-2 shadow gate. Consequence: the raw P1 shadow-vs-prod delta is
   confounded; **attribution rests on the within-arm decomposition (P1.2) and
   the prod counterfactual (P3)**, both of which hold everything except the
   floor fixed.
2. **Scorer-transfer risk**: the 2026-06-11 audit found `adaptive_mean_std`
   shape-unstable on Platt-compressed PatchTST scores (rank_score IQR 0.039;
   1.0σ dropped 86% that day). The σ-multiplier treatment is scale-free
   (defined on each session's own cross-sectional mean/std), which mitigates
   but does not eliminate this; P3 is the explicit control — no enablement
   recommendation on shadow-instrument evidence alone.
3. **Marginal-entrant end-of-chain weights are conditional on the shadow's QP
   interactions** — with a different incumbent set the QP might size
   differently; the decomposition is a first-order attribution, not a full
   counterfactual funnel.
4. **10-20 sessions is a small sample** for 20d/60d forward returns with
   overlap; HAC inference is required (§4) and the verdict memo must state the
   confidence interval, not just the point estimate.

## 8. How each #47 review blocker is fixed

| # | #47 blocker (Codex, CHANGES_REQUESTED) | Fix in this protocol |
|---|---|---|
| 1 | Same-window parameter selection: the 0.5 treatment was derived from the same inspected 11-day window used to motivate the expected lift; no clean hypothesis/evaluation split | §5: evaluation is FUTURE-ONLY (sessions strictly after merge); the 06-23 → 07-09 motivation window is labeled hypothesis-generation and excluded by construction; mid-run changes void the run |
| 2 | No quality estimand for marginal entrants: deployment/candidate-count estimands alone can approve "more invested" while silently degrading alpha | §4 P2: preregistered paired forward-return estimand (20d/60d, SPY-relative, HAC) for the marginal-entrant set vs the incumbent set, with an explicit REJECT bar; plus the P3 prod-counterfactual requirement |
| 3 | Overconfident numeric language: 0.5 presented as a near-established improvement with specific expected gains | §2: 0.5σ is explicitly a candidate treatment, not a calibrated optimum; motivation-window numbers appear only as labeled hypothesis-generation evidence; no expected-lift numbers are carried as predictions; REJECT is a declared acceptable outcome |

(#47 also received an XGB-attribution correction — the kill-rate data is from
the XGB production funnel, not PatchTST. This doc attributes it correctly in §1
and handles the shadow-instrument-vs-prod-target mismatch via P3.)

## 9. Decision rule

- **Verdict = recommendation memo** (`doc/research/`), after ≥ 10 future-only
  shadow sessions. RECOMMEND-ENABLE iff: P1 shows a deployed-fraction lift
  attributable to the floor (P1.2 decomposition), AND P2's quality bar passes
  on both the shadow instrument and the P3 prod counterfactual, AND every §6
  gate is green. Anything less: REJECT, or one declared EXTEND (§5).
- **Live enablement is a SEPARATE, gated decision**: its own PR flipping
  production `buy_floor_std_mult`, carrying the memo, a pre-registration gate,
  and Codex review — a live-book behavior change is never bundled with this
  protocol. This PR authorizes NOTHING on the live book.
- **Rollback**: a single config value — revert the shadow `buy_floor` /
  `buy_floor_std_mult` flip (one commit, config-only). Blast radius is zero by
  construction: the shadow arm runs on isolated `alpaca_shadow` state and
  places no live orders.

## 10. What this PR does NOT do

- Does not touch `configs/strategy_config.json` or
  `configs/strategy_config.golden.json` (verified by the pin test added in
  `tests/test_strategy_configs.py`).
- Does not change the 12% per-name cap, sector caps, slots, Kelly parameters,
  or any other shadow key.
- Does not authorize live enablement, a canary, or any live order.
- Does not claim 0.5σ is correct — it registers the test that will decide.

## Files changed

- `configs/strategy_config.shadow.json` — `buy_floor` →
  `adaptive_mean_std`, `buy_floor_std_mult` → 0.5, `_buy_floor_reason`
  rewritten to cite this doc (treatment arm).
- `tests/test_strategy_configs.py` — pin test: production/golden stay at
  `adaptive_mean_std` / 1.0σ; shadow carries the registered treatment.
- `doc/progress/2026-07-10-admission-breadth-shadow-ab.md` — progress record.
