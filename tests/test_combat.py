"""ComBat must remove planted site batch effects while preserving the planted biological (case-control) effect."""

import numpy as np
import pytest

from loso_replication.combat import combat
from loso_replication.loso import effect_sizes
from loso_replication.simulate import simulate_multisite


@pytest.fixture()
def dataset():
    """Dataset.

    Returns:
    The result.
    """
    return simulate_multisite(seed=42)


def _site_means(X, sites):
    return np.stack([X[sites == s].mean(axis=0) for s in np.unique(sites)])


def test_combat_removes_planted_site_effects(dataset):
    """Test combat removes planted site effects.

    Args:
    dataset: dataset.
    """
    X = dataset.X.to_numpy()
    sites = dataset.sites
    before = _site_means(X, sites).var(axis=0).mean()

    X_h = np.asarray(combat(X, sites, prefer_neurocombat=False))
    after = _site_means(X_h, sites).var(axis=0).mean()

    assert after < 0.2 * before, f"site-mean variance not reduced: {before} -> {after}"


def test_combat_preserves_biological_effect(dataset):
    """Test combat preserves biological effect.

    Args:
    dataset: dataset.
    """
    rep_idx = [dataset.X.columns.get_loc(c) for c in dataset.replicable_features]
    X = dataset.X.to_numpy()
    d_before, _ = effect_sizes(X, dataset.y)
    X_h = np.asarray(combat(X, dataset.sites, prefer_neurocombat=False))
    d_after, _ = effect_sizes(X_h, dataset.y)

    # Planted effects stay positive and strong after harmonization.
    assert np.all(d_after[rep_idx] > 0.4)
    assert np.corrcoef(d_before, d_after)[0, 1] > 0.9


def test_combat_accepts_dataframe_and_matches_array(dataset):
    """Test combat accepts dataframe and matches array.

    Args:
    dataset: dataset.
    """
    df_out = combat(dataset.X, dataset.sites, prefer_neurocombat=False)
    arr_out = combat(dataset.X.to_numpy(), dataset.sites, prefer_neurocombat=False)
    assert np.allclose(df_out.to_numpy(), arr_out)
    assert list(df_out.columns) == list(dataset.X.columns)


def test_combat_single_site_is_identity():
    """Test combat single site is identity."""
    X = np.random.default_rng(0).normal(size=(10, 5))
    out = combat(X, np.array(["a"] * 10))
    assert np.allclose(out, X)


def test_ref_batch_actually_changes_harmonization(dataset):
    """Naming a different reference site must change the harmonized output.

    ``ref_batch`` used to be validated and then discarded, so every reference
    site returned bit-for-bit the same matrix. The parameter is part of the
    public API, so a caller selecting a reference site got silently different
    harmonization from the one they asked for.

    Args:
        dataset: Simulated multi-site dataset.
    """
    X = dataset.X.to_numpy()
    by_site_0 = np.asarray(combat(X, dataset.sites, ref_batch="site_0"))
    by_site_1 = np.asarray(combat(X, dataset.sites, ref_batch="site_1"))
    assert not np.array_equal(by_site_0, by_site_1), (
        "ref_batch is ignored: naming a different reference site returned an "
        "identical matrix"
    )


def test_ref_batch_still_removes_site_effects(dataset):
    """Constraining the prior must not break the harmonization itself.

    Args:
        dataset: Simulated multi-site dataset.
    """
    X = dataset.X.to_numpy()
    before = _site_means(X, dataset.sites).var(axis=0).mean()
    for ref in ("site_0", "site_2"):
        after = _site_means(
            np.asarray(combat(X, dataset.sites, ref_batch=ref)), dataset.sites
        ).var(axis=0).mean()
        assert after < 0.2 * before, f"ref_batch={ref}: site effects not removed"


def test_ref_batch_rejects_unknown_site(dataset):
    """An unknown reference site must raise rather than fall back silently.

    Args:
        dataset: Simulated multi-site dataset.
    """
    with pytest.raises(ValueError, match="not present in sites"):
        combat(dataset.X.to_numpy(), dataset.sites, ref_batch="site_nope")


def test_ref_batch_validated_even_for_single_site():
    """A typo'd reference site must be caught even when there is one site.

    Single-site data returns unchanged (nothing to harmonize), which used to
    short-circuit before the ``ref_batch`` check.

    Returns:
        None.
    """
    X = np.random.default_rng(0).normal(size=(10, 5))
    with pytest.raises(ValueError, match="not present in sites"):
        combat(X, np.array(["only_site"] * 10), ref_batch="typo")


def test_ref_batch_with_two_sites_falls_back_without_nan(dataset):
    """Excluding the reference from the prior must not produce NaN.

    With two sites the prior would be estimated from a single batch, where a
    sample variance is undefined, so the prior must fall back to both sites.

    Args:
        dataset: Simulated multi-site dataset.
    """
    sites = np.where(dataset.sites == "site_0", "a", "b")
    out = np.asarray(combat(dataset.X.to_numpy(), sites, ref_batch="a"))
    assert np.isfinite(out).all(), "ref_batch with 2 sites produced non-finite values"
