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


def _dataset_with_one_signal_free_site(n_sites=4, n_per_site=30, n_features=20, seed=0):
    """Build a multi-site dataset in which one site has no case-control effect.

    That site yields a training set with no significant effect at all, so its
    fold leaves sign consistency and held-out significance undefined (NaN).

    Returns:
        tuple: The ``(X, y, sites)`` triple.
    """
    rng = np.random.default_rng(seed)
    sites = np.repeat([f"s{i}" for i in range(n_sites)], n_per_site)
    y = np.tile([0, 1], n_per_site * 2)
    X = rng.normal(size=(n_sites * n_per_site, n_features))
    # Strip the planted effect from the last site so it can never be significant.
    X[sites == f"s{n_sites - 1}"] = rng.normal(size=(n_per_site, n_features))
    return X, y, sites


def test_undefined_folds_do_not_poison_the_mean():
    """A single undefined fold must not turn the whole metric into NaN.

    The aggregate used to be ``np.mean`` over every fold, so one NaN — produced
    whenever a fold has no training-significant effect — wiped out the folds
    that were perfectly well defined. The reported number silently became
    null even though defined folds existed.

    Returns:
        None.
    """
    X, y, sites = _dataset_with_one_signal_free_site()
    result = LosoReplicator(alpha=0.05).run(X, y, sites)

    defined = [f.sign_consistency for f in result.folds if np.isfinite(f.sign_consistency)]
    assert defined, "fixture is broken: no fold defines sign consistency"
    assert not np.isnan(result.mean_sign_consistency), (
        "mean_sign_consistency is NaN even though defined folds exist"
    )
    assert result.mean_sign_consistency == pytest.approx(float(np.mean(defined)))
    assert result.n_defined("sign_consistency") == len(defined)


def test_n_defined_counts_each_metric_independently():
    """``n_defined`` must report the contributing fold count per metric.

    Returns:
        None.
    """
    X, y, sites = _dataset_with_one_signal_free_site()
    result = LosoReplicator(alpha=0.05).run(X, y, sites)
    for metric in ("sign_consistency", "effect_map_correlation", "heldout_significance"):
        expected = sum(np.isfinite(getattr(f, metric)) for f in result.folds)
        assert result.n_defined(metric) == expected
        assert 0 < expected <= len(result.folds)


def test_run_raises_when_every_fold_is_skipped():
    """An all-skipped run must raise instead of writing an all-null summary.

    Previously this produced zero folds and a NaN aggregate that was written to
    ``loso_run_summary.json`` and printed as "Mean sign consistency: nan",
    while the process still exited 0 — a report that cannot be wrong.

    Returns:
        None.
    """
    X, y, sites = _dataset_with_one_signal_free_site()
    with pytest.raises(ValueError, match="No LOSO fold could be evaluated"):
        LosoReplicator(alpha=0.05, min_train_sites=99).run(X, y, sites)


def test_skipped_sites_are_recorded_not_discarded():
    """A partially unusable run must name exactly which sites it dropped.

    Note that the ``min_train_sites`` guard itself is all-or-nothing — every
    fold has exactly ``n_sites - 1`` training sites — so a *partial* skip can
    only come from a site that lacks both diagnostic groups.

    Returns:
        None.
    """
    rng = np.random.default_rng(2)
    sites = np.array(["a"] * 20 + ["b"] * 20 + ["degenerate"] * 4)
    y = np.array([0, 1] * 10 + [0, 1] * 10 + [1, 1, 1, 1])
    X = rng.normal(size=(44, 8))

    result = LosoReplicator(alpha=0.05, min_train_sites=2).run(X, y, sites)
    assert result.skipped_sites == ["degenerate"]
    assert [f.held_out_site for f in result.folds] == ["a", "b"]
    assert result.summary()["held_out_site"].tolist() == ["a", "b"]


def test_site_without_both_groups_is_skipped_not_fatal():
    """A single-case site cannot yield effect sizes, and must not abort the run.

    Returns:
        None.
    """
    rng = np.random.default_rng(1)
    # Two well-formed sites, plus one site that is all cases.
    sites = np.array(["a"] * 20 + ["b"] * 20 + ["c"] * 6)
    y = np.array([0, 1] * 10 + [0, 1] * 10 + [1] * 6)
    X = rng.normal(size=(46, 8))

    result = LosoReplicator(alpha=0.05, min_train_sites=2).run(X, y, sites)
    assert result.skipped_sites == ["c"]
    assert {f.held_out_site for f in result.folds} == {"a", "b"}
