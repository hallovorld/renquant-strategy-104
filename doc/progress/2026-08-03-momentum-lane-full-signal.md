# Momentum lane v2 — risk moves from EXCLUSION to SIZING (operator directive)

**Date:** 2026-08-03 · `renquant-strategy-104` · GOAL-7

STATUS:    profile deltas 4-6 + pin test; rehearsed e2e before the PR.
WHAT:      (4) realized-vol EXCLUSION disabled — sigma-scaled sizing and the
           per-name/sector caps stay ON; (5) the foreign-ER conjunct
           (alpha_to_mu) disabled — the lane's own direction gate (positive
           momentum z) stays ON; (6) wash_sale_days=0 — a hypothetical lane
           pays no tax. LIVE lane untouched on all three.
WHY:       Measured decapitation: the model's top-10 was 9/10 semis and ~all
           were vol-gated; ranks 11-12 (MU/ASML) fell to binary wash-sale
           blocks; ranks 14-16 to the foreign ER veto — the slate showed
           ranks 13-16 and read "defensive" while the model's actual view was
           chip momentum. Operator: "我要的就是跟风买动量高的" +
           "wash sale 不能全部杀死" + "shadow 里动量模型的问题尽快修好".

EVIDENCE (rehearsal, readonly alpaca_shadow tag, 2026-08-03 21:11 PT):

```
pre-v2:  84/84 scored (28 vol-gated + 4 wash-saled pre-scoring); slate
         WELL/ROST/JNJ/FDX (ranks 13-16); 1 buy.
post-v2: 116/116 scored; slate = the REAL head: MRVL(2)/COHR(8)/INTC(10)/
         MU(11) to slots + rotation APH(+7.88%) -> LRCX(2nd overall);
         buys LRCX x1 @294.61, MRVL x1 @193.77, INTC x3 @91.00;
         sigma-sizing ACTIVE: mult 0.31/0.42 -> 1.8%/2.5% targets (vs 6.4%
         for low-vol WELL yesterday) — the designed exclusion->sizing move.
         COHR/MU sized-to-0 by the one-share floor (the #608 class, now
         visible on this lane too). verdict ECONOMIC_TRADE, rc=0.
         [VERIFIED — momentum_v2_rehearsal.log in the session scratchpad]
```

## Observed for follow-up (not hidden)

- P-CONFIG-FP preflight: "artifact lacks config fingerprint … requires
  stamped sector/config metadata" — the momentum artifact does not stamp the
  sector/config block that check wants; readonly run proceeded. Needs either
  artifact-side stamping (model repo) or a kind-scoped check — tracked with
  the wiring PR.
- One-share floor removed COHR/MU intents — the anti-high-price tilt (#608)
  now measurably binds this lane; same remedy surface as the primary.

## Revert

git revert; the lane returns to inheriting the primary's exclusion gates.
