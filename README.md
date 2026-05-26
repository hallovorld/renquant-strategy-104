# renquant-strategy-104

Policy/config repository for the active RenQuant 104 strategy.

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

Initial split source: `hallovorld/RenQuant` commit
`8f3e08d8d1ae1e402a78f4815efb59e3c7c66aa8`.

## Local Test

```bash
python -m pytest -q
```
