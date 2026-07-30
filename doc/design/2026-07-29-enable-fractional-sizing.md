# DESIGN (for operator sign-off): switch on fractional sizing for strategy-104

**Status:** proposal, not merge-targeted. **No config changed by this PR.**
The change it proposes is a live capital gate and needs explicit operator
sign-off; §8's checklist is unresolved (sequencing, the 9-row 2026-07-12
safety contract, full-funnel sim, exit/tax-lot confirmation). This document
is a discussion record until those external gates are met — hold, don't
merge as an approval of the underlying flip.

**Moved from `hallovorld/renquant-orchestrator#607`** (codex review, 2026-07-29):
the proposal edits strategy-104-owned policy and belongs in this repo, not the
orchestrator. Re-homing here also surfaced that two of the original doc's
central claims were measured against the wrong config copy — corrected below
(§1, §3) rather than carried forward silently. It also surfaced two
independent gates the original document never mentioned: an already-agreed
execution-order RFC that sequences this behind a cheaper alternative (§4),
and a more rigorous, already-reviewed safety contract for this exact change
that was staged and then never merged (§5).

---

## 1. What is being proposed

**Correction (this revision):** the original orchestrator-repo draft said
`execution.fractional_shares` is "absent entirely," reading the **umbrella's
stale copy** (`RenQuant/backtesting/renquant_104/strategy_config.json`,
`fractional` under `execution` absent) rather than this repo's pinned config —
the umbrella copy is explicitly stale/experiment-only per the multi-repo
canon. Read against the actual pinned config
(`configs/strategy_config.json` / `configs/strategy_config.golden.json`, this
repo, `main`), the block **already exists**, added 2026-07-07 alongside the
S-FRAC v2 stage-2 sizing contract (`renquant-pipeline#153`,
`doc/design/2026-07-07-104-105-cash-drag-resolution.md`), and is pinned by
`tests/test_strategy_configs.py::test_fractional_shares_contract_is_explicit_and_default_off`
`[VERIFIED — read `configs/strategy_config.json` and `.golden.json` on `main`
this session; both show identical blocks]`:

```json
"execution": {
  "fractional_shares": {
    "enabled": false,
    "min_notional": 1.0,
    "min_fractional_trade_notional": 25.0,
    "non_fractionable_tickers": []
  }
}
```

So **`min_notional` is not an open choice** — it was set to `1.0` (the broker's
fractional-order floor, `MIN_FRACTIONAL_NOTIONAL_USD` in
`renquant-pipeline/kernel/sizing.py`) on 2026-07-07, with a separate $25
anti-churn dust floor (`min_fractional_trade_notional`) already chosen
alongside it. **The actual proposal is a one-line flip: `enabled: false` →
`true`.**

`kernel/sizing.py:204` (renquant-pipeline) states the contract plainly: *"no
behaviour change unless strategy-104 opts in via
`execution.fractional_shares.enabled`."* The S-FRAC v2 machinery is built,
merged, and pinned in the pipeline. Strategy-104 has the block declared but
still defaults it OFF, per its own comment: *"keep it DEFAULT OFF until the
active-path capability gate, broker guard, and sizing-fidelity evidence are
all proven."*

## 2. What it fixes, measured

When a name's position target is below one share price, integer sizing floors
it to zero and the candidate is dropped after passing every quality gate.

2026-07-27, an unblocked session `[VERIFIED — RenQuant/logs/daily_104/2026-07-27.log]`:

```
118 tickers -> 109 candidates -> 80 (vol gate) -> 15 (weak-buy floor)
-> 4 (conviction gate) -> Kelly sizes 4/4 non-zero, avg 6.1%

TSLA  sized to 0  (remaining_cash=$9301  price=$309.22)
AMZN  NEW_BUY 1 share @ 231.33  ($231, 2.2% target)
SPG   NEW_BUY 1 share @ 231.70  ($232, 2.2% target)
EME   sized to 0  (remaining_cash=$8838  price=$742.73)

2 orders placed, $463 of $9,301 cash = 5.0% deployed
```

Size-zero skips across the visible July sessions `[VERIFIED — this session,
grep of "insufficient cash — skip" / "NEW_BUY" lines in
RenQuant/logs/daily_104/{07-02,07-10,07-13,07-27,07-28}.log; skip counts,
placed notional, and starting cash all re-derived from the raw log lines,
not carried from the prior draft]`:

| date | size-zero skips | placed / cash | deployed |
|---|---:|---|---:|
| 07-02 | 2 | $240 / $8,434 | 2.8% |
| 07-10 | 1 | $800 / $9,140 | 8.8% |
| 07-13 | 2 | $661 / $9,908 | 6.7% |
| 07-27 | 2 | $463 / $9,301 | 5.0% |
| 07-28 | 1 | $0 / $6,868 | 0% |

Names hit: TSLA ($309.22), EME ($742.73), SPG ($236.69).

## 3. What it does NOT fix — read this before expecting a large effect

On 2026-07-27 fractional sizing would have given TSLA and EME their target
notional (~$231 each) instead of zero, taking the session from **$463 to
roughly $925** `[DERIVED — 2 skipped names at the emitted 2.2% target]`. That
is still only **~10% of available cash**.

The larger constraint is the **target itself**. Kelly produced an average 6.1%
target; the emitted orders carried **2.2%**, scaled by conviction
(`conv=0.44`, `conv=0.40`) `[DERIVED — emitted log line vs the Kelly line;
mechanism not read from source]`. Fractional sizing does not touch that.

**So: fractional is necessary and not sufficient.** Anyone signing this off
expecting the idle half of the book to deploy will be disappointed. It removes
one of at least three constraints; the other two are the wash-sale block
(`renquant-pipeline#223`) and the conviction scaling of the target (unexamined).

**Correction (this revision) — the "unresolved observation" in the original
draft was a false lead.** The original text flagged `kelly_sizing.fractional =
0.5` (config) vs `fractional=0.30` (a 2026-07-27 runtime log line) as an
unresolved discrepancy needing investigation "before or alongside" this
change. Re-measured this session:

- `kelly_sizing.fractional` is the **fractional-Kelly betting fraction**
  (Thorp-style half/quarter-Kelly risk scaling) — an entirely different knob
  from `execution.fractional_shares` (whole-vs-fractional **share quantity**).
  The shared word "fractional" is a naming coincidence, not the same setting.
- The "0.5 vs 0.30" values are simply the **umbrella's stale copy** (`0.5`,
  `RenQuant/backtesting/renquant_104/strategy_config.json`) vs **this repo's
  pinned copy** (`0.3`, `configs/strategy_config.json` /
  `.golden.json`, pinned by `test_strategy_configs.py:97,382-383`)
  `[VERIFIED — read both files this session; git history of the umbrella
  copy shows `fractional: 0.5` unchanged across its whole tracked history —
  it was never `0.3`, i.e. it is a cross-repo drift, not a runtime bug]`.
  The strategy-104-owned copy (`0.3`) is canonical per the multi-repo
  ownership rule; the umbrella copy is stale/experiment-only.
- This has **no bearing on the fractional-shares decision** in this document
  — it is an unrelated config-drift footnote from the original draft's
  research, not a precondition for this proposal.

## 4. Sequencing — read before signing off

This proposal is **Phase 3** of the already-agreed cash-drag execution order
(`renquant-orchestrator doc/design/2026-07-07-104-105-cash-drag-resolution.md`
§4, RFC r2, merged to `main`):

> "Fractional shares are a separate sizing-fidelity track, not the default
> first implementation phase of cash-drag remediation. The cheaper
> non-fractional A-3 one-share initiation floor and the sleeve shadow path
> must be exhausted or shown insufficient before re-opening the active-path
> fractional rollout." (§0.4) / "Fractional shares require a fresh
> active-path justification after A-3 / sleeve evidence." (§6.3)

**Neither Phase 2 (A-3) nor the sleeve has been enabled yet**
`[VERIFIED — configs/strategy_config.json` and `.golden.json` on `main`,
`sizing.one_share_floor_enabled: false` in both]`. A-3 (the one-share
initiation floor) is fully built and tested (3 codex review rounds, 20/20
tests) and has its own enablement contract
(`doc/progress/2026-07-12-one-share-floor-enablement.md`) with a retrospective
evidence packet already on record (6/11 canonical sessions rescued, mean
rescue ~8.5% PV, zero admission displacement) — but it remains OFF pending its
own prerequisites (pipeline metrics producer + orchestrator scorecard
integration + end-to-end dry-run evidence + a separate authorization PR).

This document does not resolve that sequencing question. It surfaces it so
the operator signs off on the actual choice being made: either (a) accept this
proposal as the "fresh active-path justification" the RFC requires to jump
ahead of Phase 2, with the measured evidence in §2–3 as that justification, or
(b) finish A-3's already-built, already-cheaper enablement first and revisit
fractional shares only if a residual gap remains, per the original plan.

## 5. A more rigorous safety contract already exists for THIS exact change — unmerged

**This is not a first-time question either.** Separately from the §4
sequencing RFC, an operator risk decision to enable fractional shares
specifically was already recorded once, 2026-07-10
`[VERIFIED — renquant-strategy-104 commit eba5a36, "Recorded operator risk
decision 2026-07-10 (GOAL-6, explicit override of the stage-3
shadow/pager sequence)"]`. Review over several rounds (`fix(enable):
address 3 safety/design items`, `fix(enable): tighten... per review`, "R4
— split coverage vs liveness") walked the flag back to OFF and staged a
full enablement contract instead: `doc/progress/2026-07-12-fractional-
shares-enablement.md` — a DIFFERENT document from A-3's own
`2026-07-12-one-share-floor-enablement.md` cited in §4 — on branch
`config/operator-enablement-batch-1` at commit `2d2f43e` (PR
renquant-strategy-104#56, merged into that branch, **not `main`**; no
follow-up PR ever landed the branch's final state into main, so this
contract is orphaned, not superseded) `[VERIFIED — this session, git
log/show against the live origin remote]`.

**That contract identifies a risk this document's §7 does not mention at
all: Alpaca does not support GTC stops on fractional orders (DAY-only).**
A software-loop-resident stop is therefore the ONLY protection for a
fractional position, and that protection dies with the process. The
2026-07-12 contract formalizes this as two invariants — **state coverage**
(`fractional_stop_coverage`: every fractional position has an armed,
fresh stop registry entry, hard-gated to 1.0 before any new fractional buy)
and **execution liveness** (a measured chain: last heartbeat → stale
detection → page → ack → recovery, since coverage stays 1.0 even while the
evaluator is dead) — plus a **gross fractional notional cap** as the actual
bound on at-risk capital during a dead-process window, an 8-metric daily
monitoring contract with fail-closed missing-data handling, and named
kill/rollback triggers.

**Its own prerequisite table, all 9 rows, unresolved as of 2026-07-12.**
Reproduced **complete, with the `Owner` column**, and checked row-for-row against
the source this session — all 9 rows and their statuses match the original in the
same order `[VERIFIED — `git show
2d2f43e:doc/progress/2026-07-12-fractional-shares-enablement.md`, lines 17-27,
compared row by row this session]`. An earlier revision of this document dropped
two of the nine rows, and **both of the dropped rows were operator-owned** — which
is exactly why the omission mattered: it removed the operator's own sign-off items
from the sign-off surface. The `Owner` column is restored so that is visible
rather than inferable.

| Prerequisite | Owner | Status (2026-07-12) |
|---|---|---|
| Broker fractional contract (paper-trading round-trip evidence) | renquant-execution | Not implemented |
| **Broker-side GTC stop limitation documented and accepted** | **operator** | Assumption only |
| Stage-3 shadow packet (fractional in shadow mode + monitoring) | orchestrator | Not started |
| Software stops pager SLA | orchestrator PR #481 | Merged (dark template) |
| Dead-process at-risk-notional bound | orchestrator | Not measured |
| Fractional stop coverage invariant | orchestrator + execution | Not implemented |
| Fractional gross notional cap enforced | orchestrator + pipeline | Not implemented |
| Execution liveness chain demonstrated | orchestrator | Not measured |
| **Explicit signed-off risk decision with evidence** | **operator** | Pending above |

**The two operator-owned rows are in bold**, and neither can be discharged by an
agent: one is an acceptance of a broker limitation, the other is the signed risk
decision itself. So the row-by-row re-check this section demands cannot complete
without the operator, independently of everything else in this document.

Spot-check of current status, this session: the pager package the table cites
(`renquant-orchestrator#481`) is merged, and its OWN title still reads
"staged dark" `[VERIFIED — gh pr view 481]` — consistent with the table's
2026-07-12 status, not evidence it has since been wired live.

**What is and is not verified here, stated precisely.** The *table's fidelity to
its source* is fully verified (all 9 rows, this session). Whether each
prerequisite is *still* unresolved **today** is NOT: only the pager row was
re-checked, and the other eight rows carry their 2026-07-12 status unchanged. The
row-by-row re-check remains outstanding work, not a completed check — that
distinction is the whole point of this section. **This is a SECOND, independent gate from §4's
sequencing question — resolving §4 in favor of proceeding does not resolve
this one.** Even if the operator decides fractional shares may jump ahead
of A-3, this proposal must not be signed off against its own §7 checklist
alone without first confirming, row by row, whether the 2026-07-12
contract's prerequisites now hold.

## 6. Why the risk is lower than it looks — for the failure modes THIS document covers, excluding §5

- The **broker-side guard is the authority**, not this config.
  `sizing.py:266-271` (renquant-pipeline) documents sizing-time eligibility as
  **advisory**: the fail-closed check is `renquant-execution` stage 1
  (`is_fractionable` + no-submit classification). A name that is not
  fractionable at the broker cannot be submitted fractionally regardless of
  this flag.
- **Whole-share remains the fallback path**, not a removed one. A name that
  cannot be fractionally sized takes the existing A-3 route unchanged (when
  A-3 is itself enabled; today it stays on the plain whole-share drop).
- **A known-non-fractionable blocklist already exists**
  (`non_fractionable_tickers`, currently `[]`) and a malformed blocklist
  **fails closed for all names** `[VERIFIED — renquant-pipeline sizing.py:279]`.
- The pipeline carries `tests/test_fractional_sizing_stage2.py` (15 tests)
  covering the whole-share/fractional split.

## 7. What could go wrong

1. **Dust orders.** `min_notional=1.0` and `min_fractional_trade_notional=25.0`
   are already chosen (§1); this revision removes "choose deliberately" from
   the open checklist, but the CHOSEN values themselves have not been
   re-validated against current book size / price levels in this document.
2. **More positions, same book.** Removing the floor admits names that were
   silently dropped, so position count rises. `max_concentration = 0.12` and
   `max_position_pct = 0.15` still bind, but sector caps and the position-count
   behaviour should be re-checked against a full-funnel sim.
3. **Exit-side asymmetry.** If entries can be fractional, partial exits and the
   tax-lot logic must handle fractional quantities. This is claimed by S-FRAC
   v2 stages 0-2 but is NOT verified by this document.
4. **Settlement / buying-power interaction** with `t2_settlement_days` and
   `buying_power_mode` is unexamined here.

## 8. What must happen before this is switched on

- [ ] **Resolve the §4 sequencing question** — a fresh active-path
      justification to go ahead of A-3, or defer to A-3's enablement first.
- [ ] **Re-check the §5 contract's 9-row prerequisite table against current
      state, row by row** — independent of how §4 resolves. One row was
      spot-checked this session (pager SLA, still "dark"); the other six
      were not.
- [ ] Re-validate `min_notional=1.0` / `min_fractional_trade_notional=25.0`
      against current book size and price levels (already chosen 2026-07-07;
      not re-confirmed by this document).
- [ ] **Full-funnel sim** on the live config with the flag on vs off, per the
      live-tree mutation preflight rule — "committed = safe" is false here.
      Compare: orders placed, notional deployed, position count, sector
      exposure, and the allowed deltas to later whole-share orders (fractional
      buys consume cash, so later whole-share orders can legitimately change —
      declare the allowed bounds, then verify everything else stays within
      them, rather than asserting "no existing order changes").
- [ ] Confirm exit/tax-lot paths accept fractional quantities (risk 3).
- [ ] Operator sign-off, because this changes what reaches the broker.

## 9. Rollback

Set `execution.fractional_shares.enabled` back to `false`. The whole-share
path is unchanged and untouched by this proposal, so reverting restores
exactly today's behaviour. No artifact, model, or pin is involved.

## 10. Provenance

Figures tagged `[VERIFIED]` were read this session from
`RenQuant/logs/daily_104/2026-07-*.log`, this repo's `configs/strategy_config
{.json,.golden.json}` on `main`, and `renquant-pipeline/kernel/sizing.py` —
all read-only. `[DERIVED]` quantities are marked at the point of use. No
production surface was modified.

Related: `hallovorld/renquant-orchestrator#606` (the funnel investigation),
`hallovorld/renquant-orchestrator#607` (superseded by this PR — moved per
codex review), `renquant-pipeline#223` (wash-sale materiality),
`renquant-pipeline#224` (the misleading skip message this investigation
started from), `renquant-orchestrator doc/design/2026-07-07-104-105-cash-drag-resolution.md`
(the execution-order RFC referenced in §4).
