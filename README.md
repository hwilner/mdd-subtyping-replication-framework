# MDD Subtyping-with-Replication Framework (Paper 1)

This independent research repository plans and tracks a subtyping framework with leave-one-site-out replication built in by design, benchmarked on REST-meta-MDD Phase II. It provides harmonization and clustering utilities for transparent review and extension.

## Series position

This is **Paper 1** of the MDD subtyping series (3 papers). It is the foundation of the series; Papers 2–3 build on its framework, splits, and harmonized features.

## Research plan

| Planned work | Expected outcome |
|---|---|
| REST-meta-MDD Phase II access (open DUA) + harmonization (ComBat) | Versioned voxel/vertex-level features, 23 cohorts. |
| Subtyping-with-replication framework (normative deviations + HYDRA/Surreal-GAN-style clustering) | Method + open benchmark. |
| Leave-one-site-out replication stress test | Replication-rate results for our and published subtype schemes. |
| Release framework harness | Reused by Papers 2–3. |

**Current status:** framework implemented and validated on synthetic data; DUA to be requested; no real-data analysis has been run.

## What is included

| Path | Contents |
|---|---|
| `src/loso_replication/combat.py` | Empirical-Bayes ComBat harmonization (optional `neuroCombat` backend with built-in fallback). |
| `src/loso_replication/loso.py` | Leave-one-site-out framework: site splitting, train/test API, replication metrics (sign consistency, effect-map correlation, held-out significance). |
| `src/loso_replication/findings.py` | Registry of published MDD connectivity findings as structured effect specs. |
| `src/loso_replication/simulate.py` | Synthetic multi-site data with planted case-control effects and planted site batch shifts. |
| `src/loso_replication/io.py` | REST-meta-MDD Phase II loaders; raise clear DUA-required errors until access is approved. |
| `tests/` | Synthetic tests: ComBat removes planted site effects while preserving biology; LOSO recovers planted replicable effects and flags non-replicable ones. |
| `docs/` | Research status, methods scope, data-access steps, and contribution guidance. |

## Use and validation

```bash
pip install -e ".[dev]"
python -m pytest -q
```

## Keywords

depression, REST-meta-MDD, subtyping, normative modeling, replication, neuroimaging, reproducible research.

## Documentation

- [Introduction for new readers](docs/INTRODUCTION.md)
- [REST-meta-MDD Phase II data access](docs/DATA_ACCESS.md)
- [Contributing](CONTRIBUTING.md)
