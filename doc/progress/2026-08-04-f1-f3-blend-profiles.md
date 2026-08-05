# 2026-08-04 — F1/F3 lane profiles: the 3-component fleet variants (GOAL-9 AC2)

With pipeline#267 (BlendPanelScorer ≥2 components, equal z-sum verbatim)
merged, the two 3-component fleet variants land:

- `strategy_config.shadow_blend_rb_mom.json` — **F1**: z(prod) + z(clf) +
  z(slow momentum). Clf leg pins copied VERBATIM from the prod config's
  `shadow_models[0]` entry (content `1e644354…`, fp `1d8f167f…`); slow leg =
  the S1 profile's ledger leg (recipe fp pin).
- `strategy_config.shadow_blend_rb_fast.json` — **F3**: z(prod) + z(clf) +
  z(FAST momentum). Fast leg carries the F2 pending-first-artifact contract
  (marker present, fp/byte pins absent until the 2026-08-08 genesis batch).

Both are two-leaf-diff clones of their 2-component bases (components + lane
note), guarded MECHANICALLY by `test_f1_rb_mom_profile_semantic_pins` /
`test_f3_rb_fast_profile_semantic_pins` (the s104#89 pattern: leaf-wise
equality excluding only the declared deltas; clf pins asserted equal to the
prod entry's, F3's pending contract pinned exactly).

Tags `alpaca_shadow_blend_rb_mom` / `alpaca_shadow_blend_rb_fast` were
registered at birth (pipeline#265). Rails Step 5d/5e = next RenQuant PR
(profile-first landing order). Suite: 100 passed / 1 pre-existing env failure.
