# MDD Subtyping-with-Replication Framework

[![CI](https://github.com/hwilner/mdd-subtyping-replication-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/hwilner/mdd-subtyping-replication-framework/actions/workflows/ci.yml)

This repository builds and validates a leave-one-site-out (LOSO) replication framework for published MDD resting-state connectivity findings, with ComBat harmonization, synthetic ground-truth tests, and a DUA-gated path to REST-meta-MDD Phase II.

## Introduction

Multi-site neuroimaging findings often fail to travel because site-specific acquisition and preprocessing differences leak into model development. This project addresses that failure mode directly: published MDD connectivity findings are encoded in a registry, features are harmonized across sites, and each site's data are held out in turn so that a result must replicate at a site that contributed nothing to discovery. The repository currently contains a tested framework and a deterministic synthetic benchmark; real-data execution is gated on REST-meta-MDD Phase II DUA approval (#2).

## Extended introduction

The scientific motivation and newcomer-facing background are documented in [docs/INTRODUCTION.md](docs/INTRODUCTION.md) and [docs/EXTENDED_INTRODUCTION.md](docs/EXTENDED_INTRODUCTION.md). The conceptual pipeline is shown in [docs/figures/concept_figure.md](docs/figures/concept_figure.md): harmonize multi-site features, run LOSO replication, score sign consistency/effect-map correlation/held-out significance, and expose the result as a reusable benchmark for later MDD subtyping and prediction studies.

## Materials and methods

[docs/METHODS.md](docs/METHODS.md) specifies the implemented ComBat harmonizer, the LOSO split contract, the three replication metrics, the treatment of skipped folds, the parametric/non-parametric decision guide, and the distinction between completed synthetic validation and DUA-blocked real-data work. REST-meta-MDD Phase II access steps are in [docs/DATA_ACCESS.md](docs/DATA_ACCESS.md). Real data must not be committed; staging writes a provenance record that distinguishes synthetic demo data from post-DUA data.

### Research plan

| Issue | Task | Type | Depends on | State |
|---:|---|---|---|---|
| #1 | Implement replication framework with synthetic tests | Framework | None | Closed |
| #2 | Obtain REST-meta-MDD Phase II DUA access | Data access | None | Open |
| #3 | LOSO replication benchmark on real data | Umbrella | #1, #5 | Open |
| #4 | Results writeup and framework release | Umbrella | #3 | Open |
| #5 | Cross-site harmonization with ComBat + QC | Umbrella | #2 | Open |
| #6 | Build LOSO benchmark runner and fold configuration | Atomic | #5; uses framework from #1 | Open |
| #7 | Paper 1 figure and table scripts | Atomic | #3 | Open |
| #8 | Implement ComBat harmonization for FC/ALFF/ReHo | Atomic | #2 | Open |
| #9 | Execute all site-holdout folds and collect results | Atomic | #6 | Open |
| #10 | Pre/post-harmonization batch-effect diagnostics | Atomic | #8 | Open |
| #11 | Reproducibility re-run and release docs | Atomic | #7 | Open |
| #12 | Paper 1 manuscript draft | Atomic | #7 | Open |
| #13 | Motion and preprocessing QC report | Atomic | #8 | Open |
| #14 | Replication-rate tables and LOSO figures | Atomic | #9 | Open |
| #15 | Paper 2 handoff notes | Atomic | #7 | Open |

## Results

The committed benchmark outputs are a synthetic demonstration, not an MDD finding. They establish that the harmonization-plus-LOSO pipeline runs end to end and that its reported numbers reproduce exactly.

**Table 1. Headline synthetic LOSO benchmark results.** Source: `reports/loso/loso_run_summary.json`; full per-fold results and pre-registered real-data shells are in [docs/RESULTS.md](docs/RESULTS.md).

| Metric | Mean across 6 folds | Defined folds |
|---|---:|---:|
| Sign consistency | 0.760 | 6/6 |
| Effect-map correlation | 0.585 | 6/6 |
| Held-out significance | 0.895 | 6/6 |

The synthetic run covers 240 subjects, 60 FC features, and 6 sites, with 0 skipped sites and alpha = 0.05. Real-data result tables remain blocked on #2 and the #5 -> #6 -> #9 -> #14 execution chain.

## What is included

| Path | Contents |
|---|---|
| `src/loso_replication/combat.py` | Empirical-Bayes ComBat harmonization (optional `neuroCombat` backend with built-in fallback). |
| `src/loso_replication/loso.py` | LOSO framework: site splitting, train/test API, and replication metrics. |
| `src/loso_replication/findings.py` | Registry of eight published MDD connectivity findings as structured effect specs. |
| `src/loso_replication/simulate.py` | Synthetic multi-site data with planted case-control effects and site batch shifts. |
| `src/loso_replication/io.py` | REST-meta-MDD Phase II loaders; raise clear DUA-required errors until access is approved. |
| `src/loso_replication/staging.py` | Post-DUA staging, integrity checks, `(X, y, sites)` conversion, and synthetic demo mode. |
| `scripts/prepare_rest_meta_mdd.py` | One-command staging/validation (`--synthetic` for the demo layout). |
| `scripts/run_loso.py` | One-command LOSO benchmark runner writing `reports/loso/`. |
| `scripts/check_demo_reproducibility.py` | Fails if the committed demo benchmark numbers no longer reproduce. |
| `Makefile` | `make benchmark-demo`, `make benchmark DATA_ROOT=...`, and `make check-repro`. |
| `.github/workflows/ci.yml` | Python 3.10-3.12 tests plus staged-demo and reproducibility checks. |
| `reports/loso/` | Committed synthetic-demo benchmark outputs; real-data outputs are DUA-restricted. |
| `tests/` | Synthetic tests for harmonization, LOSO, staging, script provenance, and demo reproducibility. |
| `docs/` | Introduction, extended introduction, methods, data access, results, and figure documentation. |

## Use and validation

```bash
pip install -e ".[dev]"
python -m pytest -q
```

Every push and pull request runs the suite on Python 3.10-3.12, plus a staged-demo smoke test and a check that the committed `reports/loso/` numbers still reproduce.

Demo pipeline (no DUA needed):

```bash
make benchmark-demo
```

Confirm the committed demo numbers still reproduce:

```bash
make check-repro
```

Real-data pipeline (after DUA approval, see [docs/DATA_ACCESS.md](docs/DATA_ACCESS.md)):

```bash
make benchmark DATA_ROOT=/path/to/rest-meta-mdd
```

## Keywords

depression, REST-meta-MDD, subtyping, normative modeling, replication, neuroimaging, reproducible research.

## Documentation

- [Introduction](docs/INTRODUCTION.md)
- [Extended introduction](docs/EXTENDED_INTRODUCTION.md)
- [Materials and methods](docs/METHODS.md)
- [Results](docs/RESULTS.md)
- [REST-meta-MDD Phase II data access](docs/DATA_ACCESS.md)
- [API overview](src/loso_replication/README.md)
- [Contributing](CONTRIBUTING.md)
