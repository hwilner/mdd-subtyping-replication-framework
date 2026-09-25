# MDD Subtyping-with-Replication Framework 

This independent research repository plans and tracks a subtyping framework with leave-one-site-out replication built in by design, benchmarked on REST-meta-MDD Phase II. It provides harmonization and clustering utilities for transparent review and extension.

## Research plan

| Planned work | Expected outcome |
|---|---|
| REST-meta-MDD Phase II access (open DUA) + harmonization (ComBat) | Versioned voxel/vertex-level features, 23 cohorts. |
| Subtyping-with-replication framework (normative deviations + HYDRA/Surreal-GAN-style clustering) | Method + open benchmark. |
| Leave-one-site-out replication stress test | Replication-rate results for our and published subtype schemes. |
| Release framework harness | Reusable by later work. |

**Current status:** framework implemented and validated on synthetic data; post-DUA staging (`scripts/prepare_rest_meta_mdd.py`) and the one-command LOSO benchmark runner (`scripts/run_loso.py`) are in place and run end-to-end in `--synthetic` demo mode (demo outputs in `reports/loso/`). Real-data execution is gated only on DUA approval (issue #2); no real-data analysis has been run.

## What is included

| Path | Contents |
|---|---|
| `src/loso_replication/combat.py` | Empirical-Bayes ComBat harmonization (optional `neuroCombat` backend with built-in fallback). |
| `src/loso_replication/loso.py` | Leave-one-site-out framework: site splitting, train/test API, replication metrics (sign consistency, effect-map correlation, held-out significance). |
| `src/loso_replication/findings.py` | Registry of published MDD connectivity findings as structured effect specs. |
| `src/loso_replication/simulate.py` | Synthetic multi-site data with planted case-control effects and planted site batch shifts. |
| `src/loso_replication/io.py` | REST-meta-MDD Phase II loaders; raise clear DUA-required errors until access is approved. |
| `src/loso_replication/staging.py` | Post-DUA staging: expected file layout, integrity checks, conversion to the framework's `(X, y, sites)` structures, and a synthetic demo mode. |
| `scripts/prepare_rest_meta_mdd.py` | One-command staging/validation of downloaded DUA data (`--synthetic` for a demo layout). |
| `scripts/run_loso.py` | One-command LOSO benchmark runner: executes the moment data are staged; writes `reports/loso/`. |
| `Makefile` | `make benchmark-demo` (synthetic, no DUA) and `make benchmark DATA_ROOT=...` (real, post-DUA). |
| `reports/loso/` | Synthetic-demo benchmark outputs (fold metrics + run summary); real-data outputs are DUA-restricted. |
| `tests/` | Synthetic tests: ComBat removes planted site effects while preserving biology; LOSO recovers planted replicable effects and flags non-replicable ones; staging validation and demo roundtrip. |
| `docs/` | Research status, methods scope, data-access steps, and contribution guidance. |

## Use and validation

```bash
pip install -e ".[dev]"
python -m pytest -q
```

Demo pipeline (no DUA needed):

```bash
make benchmark-demo
```

Real-data pipeline (after DUA approval, see [docs/DATA_ACCESS.md](docs/DATA_ACCESS.md)):

```bash
make benchmark DATA_ROOT=/path/to/rest-meta-mdd
```

## Keywords

depression, REST-meta-MDD, subtyping, normative modeling, replication, neuroimaging, reproducible research.

## Documentation

- [Introduction for new readers](docs/INTRODUCTION.md)
- [REST-meta-MDD Phase II data access](docs/DATA_ACCESS.md)
- [Contributing](CONTRIBUTING.md)
