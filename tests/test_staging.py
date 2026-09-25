"""Tests for the post-DUA staging module (synthetic fixtures only)."""

import json

import numpy as np
import pandas as pd
import pytest

from loso_replication.combat import combat
from loso_replication.loso import LosoReplicator
from loso_replication.staging import (
    StagingError,
    load_staged_dataset,
    stage_synthetic_demo,
    validate_staged,
)


def test_stage_synthetic_demo_roundtrip(tmp_path):
    """Test stage synthetic demo roundtrip.

    Args:
        tmp_path: tmp path.
    """
    report = stage_synthetic_demo(tmp_path, n_sites=4, n_per_site=15,
                                  n_features=20, seed=3)
    assert report["synthetic"] is True
    assert report["n_subjects"] == 60
    assert report["n_sites"] == 4
    on_disk = json.loads((tmp_path / "STAGING_REPORT.json").read_text())
    assert on_disk["n_subjects"] == 60
    X, y, sites = load_staged_dataset(tmp_path, "FC")
    assert X.shape == (60, 20)
    assert set(np.unique(y)) == {0, 1}
    assert len(np.unique(sites)) == 4


def test_validate_rejects_missing_files(tmp_path):
    """Test validate rejects missing files.

    Args:
        tmp_path: tmp path.
    """
    with pytest.raises(StagingError, match="phenotypes.csv"):
        validate_staged(tmp_path)


def test_validate_rejects_bad_diagnosis(tmp_path):
    """Test validate rejects bad diagnosis.

    Args:
        tmp_path: tmp path.
    """
    pd.DataFrame(
        {"subject": ["a", "b"], "site": ["s1", "s2"], "diagnosis": [0, 7]}
    ).to_csv(tmp_path / "phenotypes.csv", index=False)
    pd.DataFrame({"f": [1.0, 2.0]}, index=["a", "b"]).to_csv(
        tmp_path / "features_fc.csv"
    )
    with pytest.raises(StagingError, match="binary"):
        validate_staged(tmp_path)


def test_validate_rejects_unmatched_subjects(tmp_path):
    """Test validate rejects unmatched subjects.

    Args:
        tmp_path: tmp path.
    """
    pd.DataFrame(
        {"subject": ["a", "b"], "site": ["s1", "s2"], "diagnosis": [0, 1]}
    ).to_csv(tmp_path / "phenotypes.csv", index=False)
    pd.DataFrame({"f": [1.0, 2.0]}, index=["a", "zzz"]).to_csv(
        tmp_path / "features_fc.csv"
    )
    with pytest.raises(StagingError, match="no phenotype row"):
        validate_staged(tmp_path)


def test_staged_synthetic_runs_through_loso(tmp_path):
    """The staged demo must feed the real ComBat + LOSO benchmark."""
    stage_synthetic_demo(tmp_path, seed=11)
    X, y, sites = load_staged_dataset(tmp_path, "FC")
    X_h = combat(X, sites)
    result = LosoReplicator(alpha=0.05).run(X_h, y, sites)
    assert len(result.folds) == len(np.unique(sites))
    # Planted replicable effects give clearly better-than-chance agreement
    # on synthetic data (chance is ~0.5; null features dilute the metric).
    assert result.mean_sign_consistency > 0.6
