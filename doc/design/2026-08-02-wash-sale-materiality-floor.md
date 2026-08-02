# Wash-sale materiality floor — the policy knob (design; enforcement lands in pipeline#223)

**Status:** PROPOSAL for review. This repo owns the POLICY (the knob, its
default, its enablement contract); renquant-pipeline owns the enforcement
(pipeline#223). Nothing changes behavior until (a) this merges, (b) the
pipeline consumer merges with a floor=0 behavior-invariance proof, (c) the
operator sets a non-zero floor by reviewed config PR, (d) pins advance.

## The problem this design addresses (mechanism gap, not a dollar claim)

This design stands on a MECHANISM gap that is verifiable from the code
surface alone: `wash_sale_mass_block` is a hard buy gate whose ONLY knob is
`wash_sale_days=30` — it has **no notion of how much tax a block is worth**,
no proportionality, and no governed override. That is the 07-16 incident
shape in miniature, and it holds whatever the dollar figures were on any
particular week.

In-session confirmation that the gate actively fires as a structural block:
the 2026-07-29 daily run raised `FunnelIntegrityAlert: STRUCTURAL_BLOCK` with
`wash_sale_mass_block` among the fired conditions
`[VERIFIED — logs/daily_104/2026-07-29.log, read 2026-08-02]`.

Magnitude context — CITED, not this design's decision basis: pipeline#223's
record measured ~3 of 5 sessions zeroed, roughly $15 of protected tax across
8 names (one instance $0.04) against $6,868 idle cash
`[VERIFIED — prior work, pipeline#223's own record; not re-measured here]`.
If those magnitudes had been 10× larger the design would be unchanged; only
the operator's eventual floor CHOICE (step 4) should weigh fresh magnitude
measurements, and that step has its own reviewed PR.

## The knob (this repo)

```json
"risk": {
  "wash_sale": {
    "materiality_floor_usd": 0.0,
    "_materiality_floor_note": "0.0 = floor disabled, block behavior IDENTICAL to today. When > 0: a name whose ESTIMATED foregone tax benefit from the wash-sale disallowance is <= the floor may proceed to buy; the decision record stamps the estimate, the floor, and the config fingerprint."
  }
}
```

- **Default 0.0 = today's behavior, byte-for-byte.** Turning it on is an
  explicit reviewed config change, never a code default.
- Placement under `risk` (not `execution`): this is a policy statement about
  how much tax protection justifies suppressing an admitted buy.

## The estimate contract (enforced pipeline-side, stated here as policy)

The comparison quantity is the **estimated foregone tax benefit**:
`disallowed_loss_usd × assumed_marginal_rate`, where

- `disallowed_loss_usd` uses the SAME lot engine the pipeline's tax logic
  uses, including same-event loss netting — the disposed-lot netting defect
  class must not be inherited by the estimator (a known past bug family);
- `assumed_marginal_rate` is a config constant (propose 0.40 conservative
  `[ASSUMED — proposed conservative marginal-rate constant]`);
- rounding is **UP** (ceil to the cent), so the floor systematically
  UNDER-fires: when in doubt, the block stands.
- If the estimate is UNAVAILABLE for a name (missing lot data, engine error),
  the block STANDS for that name — fail toward protection, stamped
  `estimate_unavailable`.

## AC6 governed-override shape (this LOOSENS a hard gate — the full triplet)

- **Identity:** only the operator changes the floor, via a reviewed PR to this
  repo's config; pipeline reads it from the pinned checkout. No env-var, no
  CLI override.
- **Expiry:** the floor is a standing policy, not a containment — but every
  per-decision stamp carries the config fingerprint, so any floor value is
  attributable to the exact reviewed config that set it. Raising the floor
  above a hard ceiling (propose $50 `[ASSUMED — design ceiling proposal]`)
  requires amending THIS design first —
  the pipeline consumer refuses values above the ceiling as a contract
  violation.
- **Binding:** each waived block writes a decision-trace record
  `{gate: "wash_sale", waived: true, est_foregone_tax_usd, floor_usd,
  config_fingerprint}` into the run bundle (the AC6 R4-validated surface), so
  the daily bundle answers "what was waived and under what authority" without
  archaeology.

## What this deliberately does NOT do

- No change to `wash_sale_days` or the block's detection logic.
- No per-name allowlist; the floor is uniform arithmetic.
- No effect while 0.0 — the pipeline PR must include a floor=0 A/B proving
  byte-identical decisions on a captured session (the fix-wave rule).
- Does not decide the anti-high-price tilt remedies (orch#608's switches);
  those stay their own enablement contract.

## Rollout order

1. This PR (policy + knob at 0.0).
2. pipeline#223 implementation consuming the knob (floor=0 invariance proof +
   estimator unit tests incl. the netting case + the unavailable→block case).
3. Pin advances (both repos) — operator batch.
4. Operator sets a floor (propose starting at $5
   `[ASSUMED — proposed initial operator floor]`) by reviewed config PR.
