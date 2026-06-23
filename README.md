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
- `configs/xgb_prod_artifact_manifest.json`

`xgb_prod_artifact_manifest.json` records the 2026-06-23 **operator-override
directive** (NOT a normal production promotion): XGB (alpha158_fund) runs as the
live scorer, HF PatchTST as readonly shadow. It supersedes the 2026-06-05 PatchTST
manifest. It is intentionally separate from the runtime config: the runtime reads
`strategy_config.json`, while the manifest makes the override auditable —
including the honest record that XGB did **not** pass the WF gate and is deployed
by an exceptional, withdrawable operator override behind residual controls
(`conviction_gate` mu_floor + `strict_scorer_match`), with the SPY-lag /
weak-BULL_CALM risks disclosed. See the manifest `scope_claim` for the exact,
narrowed scope (the swap beats the incumbent PatchTST; it does **not** claim an
independent edge for all-regime trading).

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
