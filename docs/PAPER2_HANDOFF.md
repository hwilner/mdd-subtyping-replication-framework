# Paper 2 handoff notes — harmonized dataset and LOSO benchmark API

Audience: the `mdd-connectivity-subtypes` project (Paper 2), which will
consume the harmonized REST-meta-MDD Phase II feature matrices and re-use
this repository's LOSO benchmark machinery.

Status: **draft against the synthetic demo** (2026-11-26). Every interface
below exists and is tested today, and the demo outputs referenced are
committed; the *real* harmonized dataset does not exist yet — it is blocked
on the DUA (#2) and harmonization execution (#8). Sections marked
"post-DUA" describe what Paper 2 will receive once those close. Nothing in
this document is a measured real-data result.

## 1. What Paper 2 will receive (post-DUA)

| Artefact | Path (post-DUA) | Status |
|---|---|---|
| Staged input layout | `$DATA_ROOT/{phenotypes.csv, features_fc.csv, features_alff.csv, features_reho.csv}` | Contract fixed; validated by `staging.validate_staged` |
| Harmonized feature matrices | Written by the #8 execution run (one per modality) | Blocked on #2/#8 |
| Input-QC report | `reports/qc/` JSON + captioned Markdown + SVG | Machinery committed (issue #13); real run blocked on #8 |
| Batch-effect diagnostics | `reports/diagnostics/` JSON + captioned Markdown | Machinery committed (issue #10); real run blocked on #8 |
| LOSO fold outputs | `reports/loso/folds/<MODALITY>/fold_<site>.json` + `manifest.json` | Demo committed; real run blocked on #9 |

Real data are DUA-restricted: they live outside the repository, are never
committed (`data/` is git-ignored), and every committed report carries a
`synthetic` provenance flag read from `STAGING_REPORT.json` — Paper 2
tooling should check that flag before quoting any number.

## 2. Staged dataset contract

- `phenotypes.csv`: one row per subject; required columns `subject`,
  `site`, `diagnosis` (1 = MDD, 0 = HC). Additional covariate columns are
  allowed and preserved (e.g. a mean-FD motion column — see §4).
- `features_<modality>.csv`: subjects × features matrix, subject IDs as
  the index, one file per modality (`fc`, `alff`, `reho`).
- `staging.validate_staged(data_root, modalities)` enforces the layout:
  binary diagnosis, no duplicate subjects, ≥ 2 sites, finite numeric
  matrices, and feature-subject ⊆ phenotype-subject alignment.
- `staging.load_staged_dataset(data_root, modality)` returns the aligned
  `(X, y, sites)` triple consumed by every downstream component.
- Harmonization entry point: `loso_replication.combat.combat(data, sites,
  *, ref_batch=None, prefer_neurocombat=True)` — empirical-Bayes ComBat,
  same type/shape out as in; `CombatHarmonizer` is the sklearn-style
  wrapper. ComBat as implemented here models site only; protecting
  biological covariates (diagnosis/age/sex) in the real run is a tracked
  design requirement on #8 (see its 2026-11-21 comment).

## 3. LOSO benchmark API

Two layers; Paper 2 can drive either.

**Library layer** — `loso_replication.loso.LosoReplicator(alpha=0.05,
min_train_sites=2, harmonize=None)`:

- `.split_sites(sites)` yields `(held_out_site, train_idx, test_idx)` per
  site; `.run(X, y, sites)` returns a `LosoResult` of per-fold
  `FoldResult`s plus `skipped_sites` (under-resourced folds are recorded,
  never silently dropped).
- Metrics per fold: sign consistency, effect-map correlation, held-out
  significance (definitions in METHODS.md).

**Config-driven runner** (recommended for reproducible consumption) —
`benchmark.run_fold(held_out_site, X, y, sites, alpha=0.05,
min_train_sites=2, harmonize=combat, modality="FC", provenance=None)`:

- Returns a JSON-serializable fold record, schema
  `loso-fold-result/v1`, keys: `held_out_site`, `n_train`, `n_test`,
  `n_cases_test`, `n_controls_test`, `status` (`completed`/`skipped`),
  `skip_reason`, `sign_consistency`, `effect_map_correlation`,
  `heldout_significance`, `n_train_significant_effects`,
  `undefined_reason`, plus `alpha`, `modality`, `harmonization`, and a
  verbatim `provenance` block.
- `benchmark.write_fold_output` serializes records deterministically
  (sorted keys, NaN/inf refused) under
  `reports/loso/folds/<modality>/fold_<site>.json`;
  `benchmark.write_manifest` / `verify_manifest` SHA-256-pin and re-verify
  the whole fold set. `scripts/run_fold.py --all` is the one-command
  driver; `reports/loso/fold_config.json` (schema in `benchmark.folds`)
  enumerates the folds with per-fold sample sizes and runnability up
  front.
- Aggregate table: `reports/loso/loso_fold_metrics.csv` (columns
  `held_out_site, n_train, n_test, sign_consistency,
  effect_map_correlation, heldout_significance`) and
  `reports/loso/loso_run_summary.json`.

## 4. QC and diagnostics artefacts

- **Input QC (issue #13)**: `scripts/run_qc_report.py` writes
  `reports/qc/qc_report_<MOD>.{json,md}` +
  `qc_feature_distributions_<MOD>.svg` — per-site motion outliers
  (mean-FD threshold 0.2 mm declared default; the FD column is
  auto-detected from `mean_fd`/`fd_mean`/`mean_framewise_displacement`/
  `framewise_displacement_mean` or passed explicitly; absent column →
  motion QC reported unavailable, never estimated), union
  exclusion/retention counts, and per-site pooled feature-distribution
  summaries. Paper 2 should consume the retained-subject set implied by
  this report before any subtype discovery.
- **Batch-effect diagnostics (issue #10)**:
  `scripts/run_diagnostics.py` writes
  `reports/diagnostics/batch_effect_diagnostics_<MOD>.{json,md}` —
  pre/post-ComBat site eta², cross-validated site-classification accuracy,
  site-mean spread, and effect-map preservation. These are the evidence
  that the harmonized matrices Paper 2 receives are site-clean.

## 5. Reproducibility contract

- `make check-repro` fails if the committed demo benchmark numbers stop
  reproducing (8 summary keys compared exactly).
- Demo regeneration: `make benchmark-demo`, `make folds-demo`,
  `make paper1-demo`, `make diagnostics-demo`, `make qc-demo` — all
  deterministic; JSON/Markdown/SVG outputs regenerate byte-identically.
- The committed demo numbers (sign consistency 0.760, effect-map
  correlation 0.585, held-out significance 0.895; QC: 6/240 planted
  outliers excluded) are synthetic-fixture validations, **not** MDD
  findings; Paper 2 must not cite them as such.

## 6. Open items before this handoff is final

1. #2 DUA approval → staging of real matrices (owner action).
2. #8 harmonization execution, including the protected-covariates
   decision recorded on the issue.
3. #13/#10 real-data QC + diagnostics runs (machinery ready).
4. #9 fold execution + #14 replication-rate tables/figures.
5. Scientific-owner review of this document (issue #15 gate).
