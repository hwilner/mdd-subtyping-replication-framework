"""Tests for the pre/post-harmonization batch-effect diagnostics (issue #10)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from loso_replication.diagnostics import (
    biological_preservation,
    cohens_d_map,
    run_batch_diagnostics,
    site_classification_accuracy,
    site_mean_spread,
    site_variance_decomposition,
)
from loso_replication.combat import combat
from loso_replication.simulate import simulate_multisite

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def dataset():
    """Synthetic multi-site dataset with planted batch shifts and effects."""
    return simulate_multisite(seed=0)


def test_eta_squared_in_unit_interval(dataset):
    """Per-feature site eta^2 must lie in [0, 1] with matching row count."""
    table = site_variance_decomposition(dataset.X, dataset.sites)
    assert len(table) == dataset.X.shape[1]
    assert table["eta_squared"].between(0.0, 1.0).all()


def test_harmonization_reduces_site_variance(dataset):
    """ComBat must reduce the mean site eta^2 of the synthetic batch shifts."""
    pre = site_variance_decomposition(dataset.X, dataset.sites)["eta_squared"].mean()
    harmonized = combat(dataset.X, dataset.sites, prefer_neurocombat=False)
    post = site_variance_decomposition(harmonized, dataset.sites)["eta_squared"].mean()
    assert post < pre * 0.5  # strong planted shifts should mostly vanish


def test_site_classification_drops_toward_chance(dataset):
    """Site must be readable pre-ComBat and near chance post-ComBat."""
    pre = site_classification_accuracy(dataset.X, dataset.sites, seed=0)
    harmonized = combat(dataset.X, dataset.sites, prefer_neurocombat=False)
    post = site_classification_accuracy(harmonized, dataset.sites, seed=0)
    assert pre["accuracy"] > 0.5  # planted batch shifts are detectable
    assert post["accuracy"] < pre["accuracy"]
    assert post["accuracy"] < pre["chance_majority"] + 0.10


def test_biological_signal_preserved(dataset):
    """The case-control effect map must survive harmonization almost intact."""
    harmonized = combat(dataset.X, dataset.sites, prefer_neurocombat=False)
    result = biological_preservation(dataset.X, harmonized, dataset.y)
    assert result["effect_map_correlation"] > 0.9
    assert result["mean_abs_d_post"] == pytest.approx(result["mean_abs_d_pre"], rel=0.25)
    # Raw sign flips may occur among noise-level effects; no meaningful
    # effect (|d| > 0.2 pre-harmonization) may change direction.
    d_pre = cohens_d_map(dataset.X, dataset.y)
    d_post = cohens_d_map(harmonized, dataset.y)
    strong = np.abs(d_pre) > 0.2
    assert (np.sign(d_pre[strong]) != np.sign(d_post[strong])).sum() == 0


def test_cohens_d_recovers_planted_effects(dataset):
    """Planted replicable features must carry the largest |d| values."""
    d = cohens_d_map(dataset.X, dataset.y)
    ranked = np.argsort(-np.abs(d))
    planted = set(dataset.replicable_features)
    top = {dataset.X.columns[i] for i in ranked[: len(planted)]}
    assert len(planted & top) >= len(planted) - 2  # allow sampling noise


def test_site_mean_spread_drops(dataset):
    """Between-site spread of feature means must shrink after harmonization."""
    pre = site_mean_spread(dataset.X, dataset.sites)
    harmonized = combat(dataset.X, dataset.sites, prefer_neurocombat=False)
    post = site_mean_spread(harmonized, dataset.sites)
    assert post["mean"] < pre["mean"]


def test_run_batch_diagnostics_deterministic(dataset):
    """The full report must be deterministic for a fixed seed."""
    first = run_batch_diagnostics(dataset.X, dataset.y, dataset.sites, seed=0)
    second = run_batch_diagnostics(dataset.X, dataset.y, dataset.sites, seed=0)
    assert first == second
    json.dumps(first)  # report must stay JSON-serializable


def test_run_batch_diagnostics_structure(dataset):
    """The report must carry the pre/post blocks and provenance fields."""
    report = run_batch_diagnostics(dataset.X, dataset.y, dataset.sites, seed=0)
    for block in ("pre", "post"):
        assert {"eta_squared_mean", "site_classification", "site_mean_spread"} <= set(report[block])
    assert report["harmonization"] == "combat (built-in empirical Bayes)"
    assert report["n_sites"] == len(np.unique(dataset.sites))


def test_input_validation():
    """Bad shapes and single-site data must raise clear errors."""
    X = pd.DataFrame(np.ones((6, 3)))
    with pytest.raises(ValueError, match="sites length"):
        site_variance_decomposition(X, np.array(["a", "b"]))
    with pytest.raises(ValueError, match="at least two sites"):
        run_batch_diagnostics(X, np.array([0, 1, 0, 1, 0, 1]), np.array(["a"] * 6))
    with pytest.raises(ValueError, match="at least 2 cases"):
        cohens_d_map(X, np.array([1, 0, 0, 0, 0, 0]))


def test_diagnostics_script_end_to_end(tmp_path):
    """The CLI must stage the demo, write both outputs, and label the scope."""
    data_root = tmp_path / "demo"
    reports_dir = tmp_path / "reports"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_diagnostics.py"),
         "--data-root", str(data_root), "--synthetic",
         "--reports-dir", str(reports_dir)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((reports_dir / "batch_effect_diagnostics_FC.json").read_text())
    assert report["synthetic"] is True
    assert report["post"]["eta_squared_mean"] < report["pre"]["eta_squared_mean"]
    md = (reports_dir / "batch_effect_diagnostics_FC.md").read_text()
    assert "synthetic demonstration" in md
    assert "Table D1" in md and "Table D2" in md


def test_diagnostics_script_refuses_unstaged_data(tmp_path):
    """The CLI must fail cleanly when no provenance record exists."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_diagnostics.py"),
         "--data-root", str(tmp_path / "empty"),
         "--reports-dir", str(tmp_path / "reports")],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 1
    assert "provenance" in result.stderr.lower() or "Stage the data" in result.stderr
