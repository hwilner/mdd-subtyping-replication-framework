# loso_replication API

Leave-one-site-out (LOSO) replication framework for published MDD
resting-state connectivity findings, with ComBat harmonization and a
synthetic ground-truth generator. Install with `pip install -e ".[dev]"`.

## `combat` — harmonization

- `combat(data, sites, *, ref_batch=None, prefer_neurocombat=True)`
  Harmonize a (n_samples, n_features) matrix across sites. Accepts and
  returns `numpy.ndarray` or `pandas.DataFrame`. Uses the optional
  `neuroCombat` package when installed; otherwise the built-in
  empirical-Bayes implementation (Johnson, Li & Rabinovic, 2007).
- `CombatHarmonizer` — sklearn-style wrapper (`fit_transform(data, sites)`).

## `loso` — replication framework

- `effect_sizes(X, y)` → `(d, p)`: per-feature Cohen's d (case − control)
  and Welch t-test p-values. `y`: 1 = MDD case, 0 = control.
- `LosoReplicator(alpha=0.05, min_train_sites=2, harmonize=None)`
  - `.split_sites(sites)` → list of `(held_out_site, train_idx, test_idx)`.
  - `.run(X, y, sites)` → `LosoResult`; `harmonize` (e.g. `combat`) is
    applied before splitting.
- `LosoResult.summary()` → per-fold DataFrame; aggregate properties
  `mean_sign_consistency`, `mean_effect_map_correlation`,
  `mean_heldout_significance`.
- Metrics per `FoldResult`: `sign_consistency` (sign agreement of
  training-significant effects on the held-out site),
  `effect_map_correlation` (train vs held-out Cohen's d maps),
  `heldout_significance` (fraction of training-significant effects at
  p < alpha held out).

## `findings` — registry

- `FINDINGS` — tuple of `Finding(key, feature, direction, modality,
  citation, doi)` for published MDD connectivity effects.
- `findings_table()` → DataFrame; `get_finding(key)` → one `Finding`.

## `simulate` — synthetic ground truth

- `simulate_multisite(n_sites=6, n_per_site=40, ..., seed=0)` →
  `SyntheticDataset(X, y, sites, replicable_features,
  nonreplicable_features, null_features, batch_shifts)` with planted
  same-direction case-control effects, planted random-sign
  (non-replicable) effects, and planted additive/multiplicative site
  batch shifts.

## `io` — real data (DUA-gated)

- `load_features(data_root, modality)`, `load_phenotypes(data_root)`,
  `load_dataset(data_root, modality)` → `(X, y, sites)`.
- All raise `DataAccessError` with DUA guidance until REST-meta-MDD
  Phase II access is approved (see `docs/DATA_ACCESS.md`).

## Example

```python
from loso_replication import simulate_multisite, combat, LosoReplicator

ds = simulate_multisite(seed=0)
X_h = combat(ds.X, ds.sites)
result = LosoReplicator().run(X_h, ds.y, ds.sites)
print(result.summary())
```
