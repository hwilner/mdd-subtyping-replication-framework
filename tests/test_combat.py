"""ComBat must remove planted site batch effects while preserving the
planted biological (case-control) effect."""

import numpy as np
import pytest

from loso_replication.combat import combat
from loso_replication.loso import effect_sizes
from loso_replication.simulate import simulate_multisite


@pytest.fixture()
def dataset():
    return simulate_multisite(seed=42)


def _site_means(X, sites):
    return np.stack([X[sites == s].mean(axis=0) for s in np.unique(sites)])


def test_combat_removes_planted_site_effects(dataset):
    X = dataset.X.to_numpy()
    sites = dataset.sites
    before = _site_means(X, sites).var(axis=0).mean()

    X_h = np.asarray(combat(X, sites, prefer_neurocombat=False))
    after = _site_means(X_h, sites).var(axis=0).mean()

    assert after < 0.2 * before, f"site-mean variance not reduced: {before} -> {after}"


def test_combat_preserves_biological_effect(dataset):
    rep_idx = [dataset.X.columns.get_loc(c) for c in dataset.replicable_features]
    X = dataset.X.to_numpy()
    d_before, _ = effect_sizes(X, dataset.y)
    X_h = np.asarray(combat(X, dataset.sites, prefer_neurocombat=False))
    d_after, _ = effect_sizes(X_h, dataset.y)

    # Planted effects stay positive and strong after harmonization.
    assert np.all(d_after[rep_idx] > 0.4)
    assert np.corrcoef(d_before, d_after)[0, 1] > 0.9


def test_combat_accepts_dataframe_and_matches_array(dataset):
    df_out = combat(dataset.X, dataset.sites, prefer_neurocombat=False)
    arr_out = combat(dataset.X.to_numpy(), dataset.sites, prefer_neurocombat=False)
    assert np.allclose(df_out.to_numpy(), arr_out)
    assert list(df_out.columns) == list(dataset.X.columns)


def test_combat_single_site_is_identity():
    X = np.random.default_rng(0).normal(size=(10, 5))
    out = combat(X, np.array(["a"] * 10))
    assert np.allclose(out, X)
