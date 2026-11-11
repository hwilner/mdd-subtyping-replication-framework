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

**Table 3. Aggregate synthetic LOSO benchmark results.** Means are over the six folds for which each metric is defined. These values are deterministic for the committed synthetic seed and are protected from silent drift by `make check-repro`.

| Metric | Mean | Defined folds | Interpretation |
|---|---:|---:|---|
| Sign consistency | 0.760 | 6/6 | Fraction of training-significant effects with the same direction at the held-out site |
| Effect-map correlation | 0.585 | 6/6 | Pearson correlation between train and held-out Cohen's d maps |
| Held-out significance | 0.895 | 6/6 | Fraction of training-significant effects that are nominally significant at the held-out site |

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
| Motion outliers/exclusions by site | — | — | — | — | Planned (#13) |
| Site-related variance before harmonization | — | — | — | — | Planned (#10) |
| Site-related variance after harmonization | — | — | — | — | Planned (#10) |
| Protected diagnosis/age/sex signal retained | — | — | — | — | Planned (#8, #10) |

## Figures

**Figure 1. Replication-framework concept schematic.** Multi-site resting-state features are harmonized with ComBat; each LOSO fold discovers effects on N-1 sites and tests them on the hidden site; replication is scored by sign consistency, effect-map correlation, and held-out significance. Source and caption: `docs/figures/concept_figure.md`; rendered asset: `docs/figures/01-concept-schematic.png`.

**Figure 2. Distribution of LOSO replication metrics across held-out sites.** Planned real-data figure; authorized by #14 after fold execution (#9). The synthetic fold metrics in Table 2 provide the plotting contract.

**Figure 3. Pre- versus post-ComBat site-effect diagnostics.** Planned real-data figure; authorized by #10 after harmonization (#8) and QC (#13).

## Validation record

**Table 6. Repository validation performed for this documentation update.** Tests exercise synthetic ComBat harmonization, LOSO splitting/metrics, staging, script provenance, and exact reproduction of the committed demo report. They do not validate scientific claims about MDD.

| Branch | Commit/context | Check | Result | Notes |
|---|---|---|---|---|
| `main` | b2d9e23 | `PYTHONPATH=$PWD:$PWD/src python -m pytest -q` | 40/40 pass (14.57 s) | Python 3.12, CPU |
| `main` | b2d9e23 | `make check-repro` | Pass | 8 committed summary keys reproduced exactly |
| `chore/daily-2026-10-02-mdd-subtyping-replication-framework` | 855eb42 | `PYTHONPATH=$PWD:$PWD/src python -m pytest -q` | 40/40 pass (13.90 s) | Same code/tests as main; branch lacks the root verification note |
| `chore/daily-2026-10-02-mdd-subtyping-replication-framework` | 855eb42 | `make check-repro` | Pass | 8 committed summary keys reproduced exactly |

The older verification note remains at `results.md`; this file is the paper-style results record used by the README going forward.
