PYTHON ?= python3
export PYTHONPATH := src:$(PYTHONPATH)

.PHONY: test doctor

test:
	$(PYTHON) -m pytest -q

doctor:
	$(PYTHON) -c "from renquant_strategy_104 import strategy_manifest; print(strategy_manifest('configs/strategy_config.json')['fingerprint']); print('renquant-strategy-104 ok')"
