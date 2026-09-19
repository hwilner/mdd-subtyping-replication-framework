"""Findings registry, IO access guards, and simulator bookkeeping."""

import numpy as np
import pytest

from loso_replication.findings import FINDINGS, findings_table, get_finding
from loso_replication.io import DataAccessError, load_dataset, load_features, load_phenotypes
from loso_replication.simulate import simulate_multisite


def test_findings_registry_wellformed():
    keys = [f.key for f in FINDINGS]
    assert len(keys) == len(set(keys))
    assert all(f.direction in (-1, 1) for f in FINDINGS)
    table = findings_table()
    assert len(table) == len(FINDINGS)
    assert get_finding(keys[0]).key == keys[0]
    with pytest.raises(KeyError):
        get_finding("does_not_exist")


def test_io_requires_dua(tmp_path):
    with pytest.raises(DataAccessError, match="Data Use Agreement"):
        load_features()
    with pytest.raises(DataAccessError):
        load_phenotypes(tmp_path / "missing")
    with pytest.raises(DataAccessError):
        load_dataset(tmp_path)  # empty dir: no files
    with pytest.raises(ValueError):
        load_features(tmp_path, modality="EEG")


def test_io_roundtrip_after_dua(tmp_path):
    ds = simulate_multisite(n_sites=3, n_per_site=10, n_features=8,
                            n_replicable=2, n_nonreplicable=2, seed=1)
    pheno = ds.X.copy()
    pheno.index = [f"sub{i:03d}" for i in range(len(ds.X))]
    pheno.to_csv(tmp_path / "features_fc.csv")
    import pandas as pd

    pd.DataFrame(
        {"subject": pheno.index, "site": ds.sites, "diagnosis": ds.y}
    ).to_csv(tmp_path / "phenotypes.csv", index=False)

    X, y, sites = load_dataset(tmp_path, "FC")
    assert X.shape == ds.X.shape
    assert np.array_equal(y, ds.y)
    assert np.array_equal(sites, ds.sites)


def test_simulator_ground_truth_partition():
    ds = simulate_multisite(seed=3)
    feats = set(ds.X.columns)
    assert set(ds.replicable_features) | set(ds.nonreplicable_features) | set(ds.null_features) == feats
    assert not (set(ds.replicable_features) & set(ds.nonreplicable_features))
    assert set(ds.batch_shifts) == set(np.unique(ds.sites))
    assert set(ds.y) == {0, 1}
