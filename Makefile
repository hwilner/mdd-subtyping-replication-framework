# One-command entry points. Real-data runs require the REST-meta-MDD
# Phase II DUA and a local data root (never committed).

.PHONY: install test stage-demo benchmark-demo benchmark

DATA_ROOT ?= data/demo

install:
	pip install -e ".[dev]"

test:
	python -m pytest -q

# Stage the synthetic demo dataset (no DUA needed).
stage-demo:
	python scripts/prepare_rest_meta_mdd.py --data-root $(DATA_ROOT) --synthetic

# Full demo: stage synthetic data, then run the LOSO benchmark.
benchmark-demo: stage-demo
	python scripts/run_loso.py --data-root $(DATA_ROOT)

# Real-data benchmark (post-DUA): make benchmark DATA_ROOT=/path/to/rest-meta-mdd
benchmark:
	python scripts/prepare_rest_meta_mdd.py --data-root $(DATA_ROOT)
	python scripts/run_loso.py --data-root $(DATA_ROOT)
