# Progress: small-n guard keys relocated to shadow-only (P0 remediation step 1)

Date: 2026-07-18

## What

Per the P0 on RenQuant#498 (review 4727377226, independent codex): remove
`buy_floor_min_n` / `buy_floor_absolute_smalln` from
`configs/strategy_config.json` and `configs/strategy_config.golden.json`
(reverting #60's activation half); enable them ONLY in
`configs/strategy_config.shadow.json` (the daily shadow arm — which runs
`adaptive_quantile`, so shadow evidence also covers the quantile small-n
branch). Production behavior returns to pre-#60 status quo; the shadow
arm begins generating the guard-active evidence the P0 requires.

## Why

The P0 is accepted: the guard keys only on finite-score count and cannot
distinguish a healthy narrow cross-section from scorer/data/feature
failure residue. Production activation now requires: eligibility-ledger
design amendment (in drafting) → implementation → shadow replay + frozen
verdict → operator authorization → new pin PR. Two-arm shadow_a/b
(epoch-frozen) untouched.
