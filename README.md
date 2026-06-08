# renquant-strategy-104

Policy/config repository for the active RenQuant 104 strategy.

Operating model: https://github.com/hallovorld/RenQuant/blob/main/doc/arch/subrepo-operating-model.md

Repository map: [RENQUANT_REPOS.md](RENQUANT_REPOS.md)

Local automation:

```bash
make test
make doctor
```

This repo owns strategy policy, not implementation:

- active/golden/shadow strategy configs
- watchlist and universe policy
- sector map and regime parameters
- gate/threshold policy
- production and shadow artifact pins

It must not contain model training code, broker execution code, QP solver
implementation, raw data, or model checkpoints.

## Configs

- `configs/strategy_config.json`
- `configs/strategy_config.golden.json`
- `configs/strategy_config.shadow.json`
- `configs/patchtst_prod_artifact_manifest.json`

`patchtst_prod_artifact_manifest.json` records the 2026-06-05 operator-directed
PatchTST production promotion boundary. It is intentionally separate from the
runtime config: the runtime still reads `strategy_config.json`, while the
manifest makes the shadow-named production checkpoint and calibrator auditable
until they are moved or aliased into prod-named artifact registry entries.

This repo is the canonical home for RenQuant 104 strategy policy. The umbrella
RenQuant repo may retain rollback copies under `backtesting/renquant_104/`, but
runtime readers must not switch to this repo until those copies are synced and
the umbrella pin is advanced to the synced commit.

Initial split source: `hallovorld/RenQuant` commit
`8f3e08d8d1ae1e402a78f4815efb59e3c7c66aa8`.

Latest production sync source: `hallovorld/RenQuant` commit
`732704bdb00c5bda6a9f6a4ee4c33523c0824286`.

## Local Test

```bash
python -m pytest -q
```
