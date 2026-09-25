"""LOSO framework on synthetic data must recover the planted replicable effect and flag the planted non-replicable effect."""

import numpy as np
import pytest

from loso_replication.combat import combat
from loso_replication.loso import LosoReplicator, effect_sizes
from loso_replication.simulate import simulate_multisite


@pytest.fixture(scope="module")
def dataset():
    """Dataset.

    Returns:
    The result.
    """
    return simulate_multisite(seed=7)


@pytest.fixture(scope="module")
def result(dataset):
    """Result.

    Args:
    dataset: dataset.

    Returns:
    The result.
    """
    X_h = np.asarray(combat(dataset.X, dataset.sites, prefer_neurocombat=False))
    return LosoReplicator(alpha=0.05).run(X_h, dataset.y, dataset.sites)


def test_all_sites_get_a_fold(dataset, result):
    """Test all sites get a fold.

    Args:
    dataset: dataset.
    result: result.
    """
    assert len(result.folds) == len(np.unique(dataset.sites))
    summary = result.summary()
    assert set(summary.columns) >= {
        "held_out_site",
        "sign_consistency",
        "effect_map_correlation",
        "heldout_significance",
    }


def test_replicable_effect_detected(dataset, result):
    """Held-out folds must replicate the planted same-direction effect."""
    rep_idx = [dataset.X.columns.get_loc(c) for c in dataset.replicable_features]
    for fold in result.folds:
        sig = fold.test_p[rep_idx] < result.alpha
        assert sig.mean() >= 0.7, f"fold {fold.held_out_site}: planted effect not significant"
        assert np.all(fold.test_d[rep_idx] > 0), "planted effect sign flipped"


def test_replication_metrics_high_for_planted_effect(dataset, result):
    """Test replication metrics high for planted effect.

    Args:
    dataset: dataset.
    result: result.
    """
    rep_idx = [dataset.X.columns.get_loc(c) for c in dataset.replicable_features]
    corrs = []
    for fold in result.folds:
        d_train_rep = fold.train_d[rep_idx]
        d_test_rep = fold.test_d[rep_idx]
        sign_cons = np.mean(np.sign(d_train_rep) == np.sign(d_test_rep))
        corrs.append(np.corrcoef(d_train_rep, d_test_rep)[0, 1])
        assert sign_cons == 1.0
    # Effect maps of ~10 planted features are small; require high average
    # cross-fold agreement rather than a per-fold cutoff.
    assert np.mean(corrs) > 0.7


def test_nonreplicable_effect_flagged(dataset, result):
    """Planted random-sign effects must replicate worse than replicable ones."""
    rep_idx = [dataset.X.columns.get_loc(c) for c in dataset.replicable_features]
    nonrep_idx = [dataset.X.columns.get_loc(c) for c in dataset.nonreplicable_features]

    rep_scores, nonrep_scores = [], []
    for fold in result.folds:
        # Train-significant non-replicable effects should often flip sign
        # or lose significance in the held-out site.
        sig_train_nonrep = np.abs(fold.train_d[nonrep_idx]) > 0
        rep_scores.append(fold.train_d[rep_idx] * fold.test_d[rep_idx])
        nonrep_scores.append(
            fold.train_d[nonrep_idx][sig_train_nonrep] * fold.test_d[nonrep_idx][sig_train_nonrep]
        )
    rep_concordance = np.mean(np.concatenate(rep_scores) > 0)
    nonrep_concordance = np.mean(np.concatenate(nonrep_scores) > 0)
    assert rep_concordance > 0.95
    assert nonrep_concordance < 0.8


def test_null_features_no_false_discovery(dataset):
    """Pooled null features should not show spurious significance."""
    X_h = np.asarray(combat(dataset.X, dataset.sites, prefer_neurocombat=False))
    null_idx = [dataset.X.columns.get_loc(c) for c in dataset.null_features]
    _, p = effect_sizes(X_h, dataset.y)
    assert (p[null_idx] < 1e-4).sum() == 0


def test_effect_sizes_requires_two_groups():
    """Test effect sizes requires two groups."""
    X = np.zeros((4, 3))
    with pytest.raises(ValueError):
        effect_sizes(X, np.array([1, 1, 1, 1]))
