# Results

This document is the paper-style results record for the MDD subtyping-with-replication framework. The only committed benchmark outputs at this stage are the deterministic synthetic demonstration under `reports/loso/`; they validate the pipeline and documentation, but they are not evidence about MDD biology. Real REST-meta-MDD Phase II analyses remain gated by the DUA task (#2) and the real-data benchmark chain (#3, #5, #6, #9, #14).

## Synthetic demonstration

**Table 1. Synthetic LOSO benchmark run summary.** Values are copied from `reports/loso/loso_run_summary.json`, whose provenance is recorded from `STAGING_REPORT.json` rather than from a command-line flag.

| Quantity | Value |
|---|---:|
| Data root | `data/demo` |
| Data modality | FC |
| Synthetic data | true |
| Provenance source | `STAGING_REPORT.json` |
| Subjects | 240 |
| Features | 60 |
| Sites | 6 |
| Completed folds | 6 |
| Skipped sites | 0 |
| Nominal alpha | 0.05 |
| Harmonization | combat (built-in empirical Bayes) |

**Table 2. Per-fold synthetic leave-one-site-out replication metrics.** Each row holds out one site, estimates case-control effects on the remaining five sites, and scores replication on the unseen site. Values are from `reports/loso/loso_fold_metrics.csv`.

| Held-out site | Train n | Test n | Sign consistency | Effect-map correlation | Held-out significance |
|---|---:|---:|---:|---:|---:|
| site_0 | 200 | 40 | 0.667 | 0.570 | 0.905 |
| site_1 | 200 | 40 | 0.750 | 0.568 | 0.812 |
| site_2 | 200 | 40 | 0.722 | 0.597 | 0.944 |
| site_3 | 200 | 40 | 0.833 | 0.633 | 0.944 |
| site_4 | 200 | 40 | 0.824 | 0.639 | 0.824 |
| site_5 | 200 | 40 | 0.765 | 0.499 | 0.941 |

Each fold of the demo benchmark is also committed as a standalone,
checksummed record under `reports/loso/folds/FC/` (with
`reports/loso/fold_config.json` enumerating the folds), produced by the
single-fold runner of issue #6 (`scripts/run_fold.py`); every per-fold
record reproduces the corresponding Table 2 row exactly, and the set
verifies against `reports/loso/folds/FC/manifest.json`.

**Table 3. Aggregate synthetic LOSO benchmark results.** Means are over the six folds for which each metric is defined. These values are deterministic for the committed synthetic seed and are protected from silent drift by `make check-repro`.

| Metric | Mean | Defined folds | Interpretation |
|---|---:|---:|---|
| Sign consistency | 0.760 | 6/6 | Fraction of training-significant effects with the same direction at the held-out site |
| Effect-map correlation | 0.585 | 6/6 | Pearson correlation between train and held-out Cohen's d maps |
| Held-out significance | 0.895 | 6/6 | Fraction of training-significant effects that are nominally significant at the held-out site |

### Batch-effect diagnostics demonstration (issue #10 machinery)

The pre/post-harmonization diagnostics of `src/loso_replication/diagnostics.py` were run on the same staged synthetic demo dataset (`make diagnostics-demo`); the machine-readable report is `reports/diagnostics/batch_effect_diagnostics_FC.json` and the rendered version is `reports/diagnostics/batch_effect_diagnostics_FC.md`. These numbers validate the diagnostics machinery on planted batch shifts — they are a synthetic demonstration, not an MDD finding. The real-data diagnostics remain planned under Table 5 (awaiting #2, #8).

**Table 3a. Synthetic site-signal diagnostics before vs. after ComBat.** Site eta^2 is the per-feature fraction of variance explained by site; site classification is the 5-fold cross-validated accuracy of a multinomial logistic regression predicting site from the features (chance = majority site fraction = 0.167); site-mean spread is the standard deviation of per-site feature means. All values are copied from the committed JSON report.

| Diagnostic | Pre-ComBat | Post-ComBat |
|---|---:|---:|
| Site eta^2 (mean over features) | 0.1845 | 0.0034 |
| Site eta^2 (max over features) | 0.4186 | 0.0100 |
| Site classification accuracy | 0.9917 | 0.0167 |
| Site-mean spread (mean over features) | 0.5634 | 0.0678 |

**Table 3b. Synthetic biological-signal preservation.** The case-control Cohen's d effect map before vs. after harmonization; the high correlation shows ComBat removed the planted batch signal without removing the planted biological signal.

| Quantity | Value |
|---|---:|
| Effect-map correlation (pre vs. post) | 0.9900 |
| Mean |d| pre-ComBat | 0.3966 |
| Mean |d| post-ComBat | 0.4161 |
| Sign flips among meaningful effects (|d| > 0.2) | 0 / 21 |

### Motion and preprocessing QC demonstration (issue #13 machinery)

The input-QC machinery of `src/loso_replication/qc.py` was run on a synthetic demo dataset staged with a planted `mean_fd` column (`make qc-demo`; staging opt-in `with_motion=True`, so the default demo dataset is unchanged). The machine-readable report is `reports/qc/qc_report_FC.json`, the rendered version `reports/qc/qc_report_FC.md`, and the per-site distribution figure `reports/qc/qc_feature_distributions_FC.svg` (deterministic SVG, regenerates byte-identically). These numbers validate the QC machinery on planted motion outliers — they are a synthetic demonstration, not an MDD finding. The real-data QC report remains planned under Table 5 (awaiting #2, #8); on real inputs without a motion column the machinery reports motion QC as unavailable rather than estimating it.

**Table 3c. Synthetic motion outliers and exclusion counts per site.** A subject is excluded when its mean framewise displacement exceeds 0.2 mm (declared default threshold; the pre-registered real-data value may differ) or its feature row contains a non-finite value. The six detected outliers are exactly the six planted ones (0/1/2 pattern across sites; recovery is exact by construction for any staging seed and is pinned by test). All values are copied from the committed JSON report.

| Site | N | Motion outliers | Data exclusions | Excluded | Retained |
|---|---:|---:|---:|---:|---:|
| site_0 | 40 | 0 | 0 | 0 | 40 |
| site_1 | 40 | 1 | 0 | 1 | 39 |
| site_2 | 40 | 2 | 0 | 2 | 38 |
| site_3 | 40 | 0 | 0 | 0 | 40 |
| site_4 | 40 | 1 | 0 | 1 | 39 |
| site_5 | 40 | 2 | 0 | 2 | 38 |
| **Total** | **240** | **6** | **0** | **6** | **234** |

**Table 3d. Synthetic per-site pooled feature-value distribution.** Mean and SD of all feature values pooled over subjects per site; the per-site mean shifts are the planted batch offsets that Table 3a quantifies before harmonization (a distribution QC view, not a statistical test). Full five-number summaries are in `reports/qc/qc_report_FC.md` Table Q2 and the committed SVG.

| Site | Mean | SD |
|---|---:|---:|
| site_0 | 0.0826 | 1.3287 |
| site_1 | 0.0277 | 1.3007 |
| site_2 | -0.2255 | 1.2712 |
| site_3 | -0.0521 | 1.3003 |
| site_4 | -0.0721 | 1.2515 |
| site_5 | 0.1155 | 1.2386 |

## Pre-registered real-data result shells

**Table 4. Replication of published MDD connectivity findings on REST-meta-MDD Phase II.** Planned primary output of the real-data benchmark; population is blocked on #2, fold execution on #3/#6/#9, and table/figure rendering on #14. No real-data analysis has been run.

| Finding key | Modality | Expected direction | Replication rate | Mean held-out effect | Direction-consistency summary | Status |
|---|---|---:|---:|---:|---|---|
| yan2019_dmn_pcc_hypo | FC | -1 | — | — | — | Awaiting DUA (#2) |
| yan2019_dmn_seed_hypo | FC | -1 | — | — | — | Awaiting DUA (#2) |
| mulders2015_sgcc_dmn_hyper | FC | +1 | — | — | — | Awaiting DUA (#2) |
| kaiser2015_dmn_hypo | FC | -1 | — | — | — | Awaiting DUA (#2) |
| kaiser2015_salience_hypo | FC | -1 | — | — | — | Awaiting DUA (#2) |
| tozzi2020_dlpfc_hypo | FC | -1 | — | — | — | Awaiting DUA (#2) |
| li2013_reho_dmn_altered | ReHo | -1 | — | — | — | Awaiting DUA (#2) |
| liu2013_alff_frontal_altered | ALFF | -1 | — | — | — | Awaiting DUA (#2) |

**Table 5. Harmonization and QC outcome summary.** Planned real-data output for the harmonization umbrella (#5), with implementation (#8), motion/preprocessing QC (#13), and pre/post-batch diagnostics (#10) tracked separately.

| Diagnostic | FC | ALFF | ReHo | Acceptance summary | Status |
|---|---:|---:|---:|---|---|
| Subjects retained after QC | — | — | — | — | Awaiting DUA (#2) |
| Motion outliers/exclusions by site | — | — | — | — | Machinery demonstrated on synthetic inputs (Table 3c); real-data run planned (#13) |
| Site-related variance before harmonization | — | — | — | — | Planned (#10) |
| Site-related variance after harmonization | — | — | — | — | Planned (#10) |
| Protected diagnosis/age/sex signal retained | — | — | — | — | Planned (#8, #10) |

## Figures

**Figure 1. Replication-framework concept schematic.** Multi-site resting-state features are harmonized with ComBat; each LOSO fold discovers effects on N-1 sites and tests them on the hidden site; replication is scored by sign consistency, effect-map correlation, and held-out significance. Source and caption: `docs/figures/concept_figure.md`; rendered asset: `docs/figures/01-concept-schematic.png`.

**Figure 2. Distribution of LOSO replication metrics across held-out sites.** Planned real-data figure; authorized by #14 after fold execution (#9). The plotting contract is locked by a demo rendering from the committed synthetic fold metrics (Table 2): `reports/paper1/make_figures.py` regenerates `reports/paper1/fig2_loso_metrics_by_site_demo.svg` (caption in `reports/paper1/fig2_caption.md`) byte-identically, guarded by `tests/test_paper1_rendering.py`. The real-data version of this figure remains planned under #14.

**Figure 3. Pre- versus post-ComBat site-effect diagnostics.** Planned real-data figure; authorized by #10 after harmonization (#8) and QC (#13).

## Validation record

**Table 6. Repository validation performed for this documentation update.** Tests exercise synthetic ComBat harmonization, LOSO splitting/metrics, staging, script provenance, and exact reproduction of the committed demo report. They do not validate scientific claims about MDD.

| Branch | Commit/context | Check | Result | Notes |
|---|---|---|---|---|
| `main` | b2d9e23 | `PYTHONPATH=$PWD:$PWD/src python -m pytest -q` | 40/40 pass (14.57 s) | Python 3.12, CPU |
| `main` | b2d9e23 | `make check-repro` | Pass | 8 committed summary keys reproduced exactly |
| `chore/daily-2026-10-02-mdd-subtyping-replication-framework` | 855eb42 | `PYTHONPATH=$PWD:$PWD/src python -m pytest -q` | 40/40 pass (13.90 s) | Same code/tests as main; branch lacks the root verification note |
| `chore/daily-2026-10-02-mdd-subtyping-replication-framework` | 855eb42 | `make check-repro` | Pass | 8 committed summary keys reproduced exactly |
| `main` | 30a010b, aaf05cf | `PYTHONPATH=$PWD:$PWD/src python -m pytest -q` | 58/58 pass (14.66 s) | Python 3.12, CPU; adds benchmark-runner and paper1-rendering tests |
| `main` | 30a010b, aaf05cf | `make check-repro` | Pass | 8 committed summary keys reproduced exactly |
| `main` | aaf05cf | `benchmark.verify_manifest("reports/loso")` | 0 problems | All 6 committed demo fold records checksum-verified |
| `main` | 8d309f4 | blob-SHA check of all 23 pushed files | 23/23 match | One SVG transcription error caught and fixed in 8d309f4 |
| `main` | b3d7075, 9d8ee60 | `python -m pytest -q` | 69/69 pass (17.11 s) | Python 3.12, CPU; adds 11 batch-diagnostics tests (issue #10 machinery) |
| `main` | b3d7075, 9d8ee60 | `make check-repro`; `make diagnostics-demo` re-run | Pass; byte-identical | 8 committed summary keys reproduced exactly; diagnostics outputs deterministic on re-run |
| `main` | issue-#13 QC change set | `python -m pytest -q` | 82/82 pass (20.00 s) | Python 3.12, CPU; adds 13 input-QC tests (issue #13 machinery) |
| `main` | issue-#13 QC change set | `make check-repro`; `make qc-demo` re-run | Pass; byte-identical | 8 committed summary keys reproduced exactly; QC JSON/Markdown/SVG outputs deterministic on re-run |

The older verification note remains at `results.md`; this file is the paper-style results record used by the README going forward.
