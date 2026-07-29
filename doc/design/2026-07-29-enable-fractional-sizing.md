# DESIGN (for operator sign-off): switch on fractional sizing for strategy-104

**Status:** proposal. **No config changed by this PR.** The change it proposes
is a live capital gate and needs explicit sign-off.

**The change itself is four lines of config.** The reason this is a design doc
and not a flag flip is that it alters what reaches the broker.

---

## 1. What is being proposed

Add to `configs/strategy_config.json` (this repo's pinned production config —
also mirror into `configs/strategy_config.golden.json` per this repo's
active==golden contract):

```json
"execution": {
  "fractional_shares": {
    "enabled": true,
    "min_notional": <TBD, see §7>
  }
}
```

Today that block is **absent entirely**. The live `execution` object holds only
`_settlement_reason_2026_05_24`, `enabled`, `t2_settlement_days`,
`buying_power_mode` `[VERIFIED — live strategy_config.json]`.

`kernel/sizing.py:204` states the contract plainly: *"no behaviour change
unless strategy-104 opts in via `execution.fractional_shares.enabled`"*. The
S-FRAC v2 machinery is built, merged and pinned in the pipeline. **The flag
is off today, and has been since it landed** — but this is not a first-time
question: see §4 for a prior operator-authorized attempt to opt in that was
walked back to OFF during review, not simply never considered.

## 2. What it fixes, measured

When a name's position target is below one share price, integer sizing floors
it to zero and the candidate is dropped after passing every quality gate.

2026-07-27, an unblocked session `[VERIFIED — logs/daily_104/2026-07-27.log]`:

```
118 tickers -> 109 candidates -> 80 (vol gate) -> 15 (weak-buy floor)
-> 4 (conviction gate) -> Kelly sizes 4/4 non-zero, avg 6.1%

TSLA  sized to 0  (remaining_cash=$9301  price=$309.22)
AMZN  NEW_BUY 1 share @ 231.33  ($231, 2.2% target)
SPG   NEW_BUY 1 share @ 231.70  ($232, 2.2% target)
EME   sized to 0  (remaining_cash=$8838  price=$742.73)

2 orders placed, $463 of $9,301 cash = 5.0% deployed
```

Size-zero skips across the visible July sessions `[VERIFIED]`:

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
(pipeline#223) and the conviction scaling of the target (unexamined).

**Resolved** (was an open discrepancy in an earlier revision): the "config
says 0.5" reading came from `RenQuant/backtesting/renquant_104/
strategy_config.json` — a COMMITTED SNAPSHOT COPY inside the umbrella repo
(mtime 2026-07-26 06:30), not the actual config source the live pipeline
reads. `model_freshness_monitor.py:279` resolves the live path as
`renquant-strategy-104/configs/strategy_config.json` — the pinned subrepo's
own checkout, per `subrepos.lock.json`'s `renquant-strategy-104` entry
(pinned commit `8402a629`). At that exact pinned commit, `kelly_sizing.
fractional = 0.3` `[VERIFIED — git show 8402a6297ec07e316f8c8a19b403ae8b5af4
e64d:configs/strategy_config.json]`, matching the runtime log exactly — the
live config and the live runtime AGREE. The umbrella's snapshot copy is
simply STALE: strategy-104's own repo committed the 0.5→0.3 change same-day
2026-07-26 at 15:41, nine hours after the umbrella snapshot was last synced
at 06:30, and nothing has re-synced it since. This is a `RenQuant/
backtesting/renquant_104/` freshness gap independent of this proposal — not
chased further here, since it does not affect what actually governs the live
daily-104 run — but it means anyone reading config values from that umbrella
path should not assume they are current.

## 4. A more rigorous safety contract already exists for this exact change — unmerged

**This is not a first-time question.** An operator risk decision to enable
fractional shares was recorded once before, 2026-07-10
`[VERIFIED — renquant-strategy-104 commit eba5a36, "Recorded operator risk
decision 2026-07-10 (GOAL-6, explicit override of the stage-3
shadow/pager sequence)"]`. Review over several rounds (`fix(enable): address
3 safety/design items`, `fix(enable): tighten... per review`, "R4 — split
coverage vs liveness") walked the flag back to OFF and staged a full
enablement contract instead: `doc/progress/2026-07-12-fractional-shares-
enablement.md`, on branch `config/operator-enablement-batch-1` at commit
`2d2f43e` (PR renquant-strategy-104#56, merged into that branch — **not
main**; no follow-up PR ever landed the branch's final state into main, so
this contract is orphaned, not superseded) `[VERIFIED — this session, git
log/show against the live origin remote]`.

**That contract identifies the risk this proposal's §6 does not mention at
all: Alpaca does not support GTC stops on fractional orders (DAY-only).**
A software-loop-resident stop is therefore the ONLY protection for a
fractional position, and that protection dies with the process. The 2026-07
contract formalizes this as two invariants — **state coverage**
(`fractional_stop_coverage`: every fractional position has an armed,
fresh stop registry entry, hard-gated to 1.0 before any new fractional buy)
and **execution liveness** (a measured chain: last heartbeat → stale
detection → page → ack → recovery, since coverage stays 1.0 even while the
evaluator is dead) — plus a **gross fractional notional cap** as the actual
bound on at-risk capital during a dead-process window, an 8-metric daily
monitoring contract with fail-closed missing-data handling, and named
kill/rollback triggers.

**Its own prerequisite table, unresolved as of 2026-07-12** (not re-verified
line-by-line in this pass — spot-checked one row below):

| Prerequisite | Status (2026-07-12) |
|---|---|
| Broker fractional contract (paper-trading round-trip evidence) | Not implemented |
| Stage-3 shadow packet (fractional in shadow mode + monitoring) | Not started |
| Software stops pager SLA | Merged, but "dark template" |
| Dead-process at-risk-notional bound | Not measured |
| Fractional stop coverage invariant | Not implemented |
| Fractional gross notional cap enforced | Not implemented |
| Execution liveness chain demonstrated | Not measured |

Spot-check, this session: the pager package the table cites
(`renquant-orchestrator#481`) is merged, and its OWN title still reads
"staged dark" `[VERIFIED — gh pr view 481]` — consistent with the table's
2026-07-12 status, not evidence it has since been wired live. The other six
rows were not re-checked; **this proposal must not be signed off against its
own §7 checklist alone** without first confirming, row by row, whether the
2026-07-12 contract's prerequisites now hold — because that contract, not
this document's shorter one, is what the last review round decided was the
actual bar for this flag.

## 5. Why the risk is lower than it looks — for the failure modes THIS document covers

The dead-process/stop-coverage risk above is NOT addressed by anything
below; §4 is the load-bearing risk assessment for this proposal until the
2026-07-12 contract's prerequisites are checked. What follows only narrows
the risks this document originally scoped:

- The **broker-side guard is the authority**, not this config.
  `sizing.py:266-271` documents sizing-time eligibility as **advisory**: the
  fail-closed check is `renquant-execution` stage 1 (`is_fractionable` +
  no-submit classification). A name that is not fractionable at the broker
  cannot be submitted fractionally regardless of this flag.
- **Whole-share remains the fallback path**, not a removed one. A name that
  cannot be fractionally sized takes the existing A-3 route unchanged.
- **A known-non-fractionable blocklist already exists**
  (`execution.fractional_shares.non_fractionable_tickers`) and a malformed
  blocklist **fails closed for all names** `[VERIFIED — sizing.py:279]`.
- The pipeline carries `tests/test_fractional_sizing_stage2.py` (15 tests)
  covering the whole-share/fractional split.

## 6. What could go wrong

**Read §4 first — the dead-process/stop-coverage risk it describes is the
biggest one and is not repeated in this list.**

1. **Dust orders.** Small targets produce small fractional notionals. This is
   what `min_notional` is for; it must be set deliberately (§7), not defaulted.
2. **More positions, same book.** Removing the floor admits names that were
   silently dropped, so position count rises. `max_concentration = 0.12` and
   `max_position_pct = 0.15` still bind, but sector caps and the position-count
   behaviour should be re-checked against a full-funnel sim.
3. **Exit-side asymmetry.** If entries can be fractional, partial exits and the
   tax-lot logic must handle fractional quantities. This is claimed by S-FRAC
   v2 stages 0-2 but is NOT verified by this document.
4. **Settlement / buying-power interaction** with `t2_settlement_days` and
   `buying_power_mode` is unexamined here.

## 7. What must happen before this is switched on

- [ ] **Re-check the 2026-07-12 contract's 9-row prerequisite table (§4)
      against current state, row by row.** This proposal's own checklist
      below is not a substitute — it is narrower than what the last review
      round on this exact change decided was necessary. If any row is still
      unmet (one spot-checked in §4 and still appears unmet), either close
      it or explicitly re-register a smaller/different risk acceptance than
      2026-07-10's, with the same rigor.
- [ ] Choose `min_notional` explicitly, with the reasoning recorded. A floor
      that is too low creates dust; too high reproduces the current problem.
- [ ] **Full-funnel sim** on the live config with the flag on vs off, per the
      live-tree mutation preflight rule — "committed = safe" is false here.
      **"No existing order changes" is NOT the bar** — a previously-skipped
      candidate that now fills consumes cash, which can legitimately shift
      the size (or admission via the MIN-1-SHARE rule) of a LATER-ranked
      candidate in the same session, since orders are sequenced against one
      shared cash pool. The invariant S-FRAC v2 actually claims is narrower:
      `target_pct`/`target_notional` (the pre-quantization risk-budget
      output of `sizing_target_notional`) is IDENTICAL per candidate between
      flag-on and flag-off runs — fractional sizing changes whether a
      sub-1-share target deploys, never the target itself or which
      candidates are admitted. Verify THAT per-candidate invariant directly,
      then treat every order-level difference as either (a) a
      previously-size-zero candidate now filling, or (b) a downstream order
      whose share count changed only because an upstream fill consumed cash
      — and confirm (b)'s new size is still consistent with
      `compute_position_size` given the reduced investable cash, not an
      unexplained divergence. Compare orders placed, notional deployed,
      position count, and sector exposure as before.
- [ ] Confirm exit/tax-lot paths accept fractional quantities (risk 3).
- [ ] Operator sign-off, because this changes what reaches the broker.

## 8. Rollback

Remove the `execution.fractional_shares` block, or set `enabled: false`. The
whole-share path is unchanged and untouched by this proposal, so reverting
restores exactly today's behaviour. No artifact, model, or pin is involved.

## 9. Provenance

All figures `[VERIFIED]` from `RenQuant/logs/daily_104/2026-07-*.log`, the live
`strategy_config.json`, and `renquant-pipeline/kernel/sizing.py` — all read
READ-ONLY. The two `[DERIVED]` quantities are marked at the point of use. No
production surface was modified.

Related: hallovorld/renquant-orchestrator#606 (the funnel investigation),
renquant-pipeline#223 (wash-sale materiality), renquant-pipeline#224 (the
misleading skip message this investigation started from).
