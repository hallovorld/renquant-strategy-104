# CLAUDE.md

Canonical operating model:
https://github.com/hallovorld/RenQuant/blob/main/doc/arch/subrepo-operating-model.md

Local repo map: `RENQUANT_REPOS.md`.

Branch policy: `main` is the stable interface consumed by other repos and
automation. Experiments, optimizations, and large upgrades happen on feature
branches, then merge back only after tests and integration checks pass.

## Repo Role

`renquant-strategy-104` owns active strategy policy and configuration for
RenQuant 104. It is a config repo, not an implementation repo.

## Hard Boundaries

- Own configs, watchlists, universe policy, gates, thresholds, sector maps, and
  artifact pins.
- Do not add model training code, runtime decision-tree implementation, broker
  execution, QP solver internals, raw data, or model checkpoints.
- Big policy changes use a feature branch and must include config validation.
- Do not delete or empty the source umbrella repo at
  `/Users/renhao/git/github/RenQuant`.

## Workflow

- Config updates must keep active/golden/shadow intent explicit.
- Treat `configs/strategy_config*.json` as canonical. If RenQuant umbrella
  rollback copies are still present, keep them JSON-equivalent before routing
  live jobs to this repo or advancing the umbrella pin.
- Runtime code that consumes this repo must fail closed on missing or malformed
  config.
- Run before commit:

```bash
make test
make doctor
```
