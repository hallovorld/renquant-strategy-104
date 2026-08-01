## What & why

<!-- Bottom line first: the conclusion and the decision needed. -->

## Evidence

<!-- Every number carries a provenance tag: [本次实测/早前实测/推导/假设]. -->

## Checklist

- [ ] `make test` green, count stated.
- [ ] Progress doc under `doc/progress/<date>-<slug>.md`.
- [ ] **Gate design rule (GOAL-5 AC6):** if this PR adds or tightens a HARD
      capital-admission gate — one that can take a name or the book from
      tradeable → not-tradeable, as opposed to a market decision — the progress
      or design doc states its **governed override path**:
      - **identity** — who lifts it, via what *reviewed* surface;
      - **expiry** — an explicit restore condition plus an auto-alarm.
        "Temporary" is not an expiry; "until X is deployed" is;
      - **binding** — scoped by fingerprint, with the override's provenance
        carried in the run bundle.

      A true kill-switch says so explicitly. **N/A if this PR adds no such gate.**

      **In this repo the gate is usually a CONFIG VALUE, and this is the easiest
      place in the programme to miss it.** Measured 2026-07-31: this repo holds
      **1** Python file matching the gate-code pattern, out of **8** Python files
      in total — so a code-shaped reading of "does this PR add a gate?" answers
      *no* almost always. But `configs/strategy_config*.json` carries the
      **threshold values that pipeline's gates read**. Tightening a veto
      threshold, lowering a cap, or flipping an `*_enabled` flag here **is a gate
      change in effect**, executed by code in another repo. The item applies to
      config edits exactly as it does to code.

      Canonical rule: Universal Rule §7 in the umbrella
      `doc/arch/subrepo-operating-model.md`; rationale and worked examples in
      `renquant-orchestrator` `doc/design/2026-07-20-ac6-gate-design-rule.md`.

> **This checklist item is a review surface, not enforcement.** Nothing mechanical
> rejects a run bundle that omits override provenance today — measured
> 2026-07-31, `renquant-orchestrator` #690: the shared `LiveRunBundle` schema
> declares 7 fields and silently drops the rest, so a provenance field added to
> that path would be validated by nothing. Until that is fixed, this item and the
> reviewer reading it *are* the gate.

<!-- AC6 R2 rollout, tracked in renquant-orchestrator#564. -->
