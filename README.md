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

**Current status:** planning stage; DUA to be requested; no analysis has been run.

## What is included

| Path | Contents |
|---|---|
| `src/` | Harmonization, normative-deviation, and clustering utilities. |
| `tests/` | Synthetic tests with planted site effects. |
| `docs/` | Research status, methods scope, and contribution guidance. |

## Use and validation

```bash
python -m pytest -q
```

## Keywords

depression, REST-meta-MDD, subtyping, normative modeling, replication, neuroimaging, reproducible research.

## Documentation

- [Introduction for new readers](docs/INTRODUCTION.md)
