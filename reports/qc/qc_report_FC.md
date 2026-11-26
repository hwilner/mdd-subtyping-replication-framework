# Motion and preprocessing QC report (inputs only)

Scope: synthetic demonstration — validates the QC machinery, not an MDD finding. Data root `data/demo`, modality FC.

**Table Q1. Motion outliers and exclusion counts per site.** A subject is excluded when its mean framewise displacement (`mean_fd`) exceeds 0.2 mm (declared default; pre-registered value for the real run may differ) or its feature row contains a non-finite value. Offending subject IDs are listed in the JSON report.

| Site | N | Motion outliers | Data exclusions | Excluded | Retained |
|---|---:|---:|---:|---:|---:|
| site_0 | 40 | 0 | 0 | 0 | 40 |
| site_1 | 40 | 1 | 0 | 1 | 39 |
| site_2 | 40 | 2 | 0 | 2 | 38 |
| site_3 | 40 | 0 | 0 | 0 | 40 |
| site_4 | 40 | 1 | 0 | 1 | 39 |
| site_5 | 40 | 2 | 0 | 2 | 38 |
| **Total** | **240** | **6** | **0** | **6** | **234** |

**Table Q2. Per-site pooled feature-value distribution.** Five-number summary, mean, and SD of all feature values pooled over subjects per site (a distribution QC view: scanner scaling shifts show up here). The matching figure is `qc_feature_distributions_FC.svg`.

| Site | Mean | SD | Min | Q1 | Median | Q3 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| site_0 | 0.0826 | 1.3287 | -4.3281 | -0.7856 | 0.0836 | 0.9654 | 4.8011 |
| site_1 | 0.0277 | 1.3007 | -4.2336 | -0.8609 | 0.0315 | 0.8859 | 4.9248 |
| site_2 | -0.2255 | 1.2712 | -5.8146 | -1.0449 | -0.1674 | 0.5861 | 4.5478 |
| site_3 | -0.0521 | 1.3003 | -5.2272 | -0.9025 | -0.0818 | 0.8057 | 4.8363 |
| site_4 | -0.0721 | 1.2515 | -5.2559 | -0.8824 | -0.0451 | 0.7612 | 3.8963 |
| site_5 | 0.1155 | 1.2386 | -4.5857 | -0.6931 | 0.1409 | 0.9472 | 4.8073 |
