# Introduction — MDD Subtyping Replication Framework

**Series note:** This is **Paper 1 of 3** in the MDD subtyping series. It is the **foundation paper**: it builds the harmonized REST-meta-MDD Phase II dataset and the replication-analysis framework that Paper 2 (`mdd-connectivity-subtypes`) and Paper 3 (`mdd-ssri-response-prediction`) directly reuse.

## Background

Neuroimaging studies of major depressive disorder (MDD) report inconsistent resting-state connectivity differences, and published connectivity-based subtypes replicate poorly across cohorts. REST-meta-MDD Phase II provides multi-site resting-state fMRI with harmonized preprocessing, offering a rare opportunity to quantify — and fix — cross-site non-replication before proposing new subtypes.

## Research questions

1. How well do published MDD connectivity findings replicate across the ~25 REST-meta-MDD Phase II sites?
2. How much residual site/scanner batch effect remains after standard harmonization (e.g., ComBat)?
3. What benchmark protocol (leave-one-site-out) gives an honest estimate of cross-site generalization for downstream subtype papers?

## Data

| Dataset | Size | Content | Access |
| --- | --- | --- | --- |
| REST-meta-MDD Phase II | ~2,400 subjects, ~25 sites | Preprocessed resting-state fMRI (ALFF/ReHo/FC matrices) + phenotypes | DUA via R-fMRI Maps Project |

## Methods

- Cross-site harmonization with ComBat; QC of motion and preprocessing residuals.
- Leave-one-site-out replication framework: train/discover on N-1 sites, test on the held-out site.
- Synthetic-data unit tests to validate the framework before touching real data.

## Expected contributions

- A harmonized, QC'd REST-meta-MDD Phase II resource with documented batch-effect diagnostics.
- An open replication-benchmark framework reused by Papers 2 and 3.

## Scope and boundary

- No new subtype discovery here (that is Paper 2); no treatment-response prediction (Paper 3).
- Only resting-state fMRI from REST-meta-MDD; no external cohorts in this paper.
