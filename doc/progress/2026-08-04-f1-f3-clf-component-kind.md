# 2026-08-04 — F1/F3: the clf component's `kind` belonged to the wrong vocabulary

## Measured on F1's very first execution (Step 5d, 21:02 PT)

```
load_blend_scorer: component[0] panel-ltr.alpha158_fund.json verified (…)
LoadScorerTask: failed to load blend artifact … — blend component[1] declares
  unknown kind 'xgb' — supported: 'panel' (default, direct artifact) …
Panel scoring contract failed (panel_scorer_load_failed). Cleared 83 buy candidate(s)
```

The F1/F3 profiles copied the clf leg VERBATIM from the prod config's
`ranking.panel_scoring.shadow_models[0]`, pins and all — including
`kind: "xgb"`. But `shadow_models[]` and `components[]` are **different
namespaces**: shadow-model kinds name the SCORER FAMILY (`xgb`,
`hf_patchtst`), blend-component kinds name the COMPONENT LOADER
(`panel` = direct artifact, `momentum_residual` = ledger-served). Copying the
name across cost the lane its first session — the "read the contract, not the
name" failure mode, in its purest form.

## Fix

`kind` is now OMITTED on the clf component in both profiles (absent = the
loader's default `panel`, which is exactly right: the clf artifact IS a
standard panel scorer). The identity pins stay verbatim from the prod entry.

## Guard

`test_every_blend_component_kind_is_in_the_loader_vocabulary` walks EVERY
blend profile in the repo — prod included, since prod is a blend now — and
asserts each component's declared kind is absent or in
`{panel, momentum_residual}`, with an anti-vacuity floor of 10 components
checked. The two vocabularies can no longer be conflated silently.

Suite: 43 passed.
