"""Tests for the motion/preprocessing input-QC machinery (issue #13)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from loso_replication.qc import (
    DEFAULT_MOTION_THRESHOLD_MM,
    detect_motion_column,
    exclusion_table,
    feature_distribution_by_site,
    motion_outlier_table,
    run_qc_report,
)
from loso_replication.simulate import simulate_motion, simulate_multisite
from loso_replication.staging import stage_synthetic_demo

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def phen_with_motion():
    """Phenotypes table with a known motion column and planted outliers."""
    rng_subjects = [f"sub{i:04d}" for i in range(12)]
    return pd.DataFrame(
        {
            "subject": rng_subjects,
            "site": ["a"] * 6 + ["b"] * 6,
            "diagnosis": [0, 1] * 6,
            "mean_fd": [0.10, 0.12, 0.25, 0.11, 0.09, 0.13,
                        0.14, 0.08, 0.10, 0.31, 0.12, 0.11],
        }
    )


def test_detect_motion_column_candidates(phen_with_motion):
    """Auto-detection finds candidate columns and respects explicit names."""
    assert detect_motion_column(phen_with_motion) == "mean_fd"
    renamed = phen_with_motion.rename(columns={"mean_fd": "fd_mean"})
    assert detect_motion_column(renamed) == "fd_mean"
    assert (
        detect_motion_column(renamed, motion_column="fd_mean") == "fd_mean"
    )


def test_detect_motion_column_absent_returns_none(phen_with_motion):
    """No motion column means no motion QC — never a silent fallback."""
    dropped = phen_with_motion.drop(columns=["mean_fd"])
    assert detect_motion_column(dropped) is None
    table = motion_outlier_table(dropped)
    assert table["available"] is False
    assert table["total_outliers"] is None


def test_detect_motion_column_explicit_missing_raises(phen_with_motion):
    """An explicit but absent column is an error, not a fallback."""
    with pytest.raises(ValueError, match="not in phenotypes"):
        detect_motion_column(phen_with_motion, motion_column="fd")


def test_motion_outliers_exact_on_fixture(phen_with_motion):
    """Outliers are exactly the subjects above the threshold, per site."""
    table = motion_outlier_table(phen_with_motion)
    assert table["available"] is True
    assert table["threshold_mm"] == DEFAULT_MOTION_THRESHOLD_MM
    assert table["per_site"]["a"]["outlier_subjects"] == ["sub0002"]
    assert table["per_site"]["b"]["outlier_subjects"] == ["sub0009"]
    assert table["total_outliers"] == 2
    assert table["per_site"]["a"]["n_subjects"] == 6


def test_simulated_motion_ground_truth_recovered():
    """Every planted outlier — and only those — is detected, for any seed."""
    for seed in (0, 1, 7):
        sites = np.repeat([f"site_{s}" for s in range(6)], 40)
        fd, planted = simulate_motion(sites, seed=seed)
        phen = pd.DataFrame(
            {
                "subject": [f"sub{i:04d}" for i in range(len(sites))],
                "site": sites,
                "diagnosis": 0,
                "mean_fd": fd,
            }
        )
        table = motion_outlier_table(phen)
        detected = np.zeros(len(sites), dtype=bool)
        for block in table["per_site"].values():
            for sub in block["outlier_subjects"]:
                detected[int(sub[3:])] = True
        assert planted.sum() == 6  # 0+1+2 pattern over six sites
        assert (detected == planted).all()
        # Baseline is bounded below the default threshold by construction.
        assert fd[~planted].max() < DEFAULT_MOTION_THRESHOLD_MM
        assert fd[planted].min() > DEFAULT_MOTION_THRESHOLD_MM


def test_exclusion_table_unions_criteria():
    """Exclusions are the union of motion and data-quality criteria."""
    phen = pd.DataFrame(
        {
            "subject": ["s1", "s2", "s3", "s4"],
            "site": ["a", "a", "b", "b"],
            "diagnosis": [0, 1, 0, 1],
            "mean_fd": [0.10, 0.50, 0.10, 0.12],
        }
    )
    X = pd.DataFrame(
        [[1.0, 2.0], [3.0, 4.0], [np.nan, 1.0], [0.0, 1.0]],
        index=["s1", "s2", "s3", "s4"],
    )
    table = exclusion_table(phen, X)
    assert table["per_site"]["a"] == {
        "n_total": 2,
        "n_motion_excluded": 1,
        "n_data_excluded": 0,
        "n_excluded": 1,
        "n_retained": 1,
    }
    assert table["per_site"]["b"]["n_data_excluded"] == 1
    assert table["n_excluded"] == 2
    assert table["n_retained"] == 2


def test_exclusion_table_without_motion_column():
    """Without a motion column, exclusions come from data quality only."""
    phen = pd.DataFrame(
        {
            "subject": ["s1", "s2"],
            "site": ["a", "a"],
            "diagnosis": [0, 1],
        }
    )
    X = pd.DataFrame([[1.0], [np.inf]], index=["s1", "s2"])
    table = exclusion_table(phen, X)
    assert table["motion_criterion"] is None
    assert table["n_excluded"] == 1


def test_feature_distribution_by_site_values():
    """Per-site pooled summaries match a hand-computed fixture."""
    X = pd.DataFrame(
        [[0.0, 1.0], [2.0, 3.0], [10.0, 10.0]],
        index=["s1", "s2", "s3"],
    )
    sites = np.array(["a", "a", "b"])
    dist = feature_distribution_by_site(X, sites)["per_site"]
    assert dist["a"]["n_values"] == 4
    assert dist["a"]["mean"] == pytest.approx(1.5)
    assert dist["a"]["min"] == 0.0
    assert dist["a"]["max"] == 3.0
    assert dist["a"]["median"] == pytest.approx(1.5)
    assert dist["b"]["mean"] == pytest.approx(10.0)


def test_run_qc_report_deterministic():
    """The full report is byte-deterministic for a fixed synthetic seed."""
    ds = simulate_multisite(seed=0)
    X = ds.X.copy()
    X.index = [f"sub{i:04d}" for i in range(len(X))]
    fd, _ = simulate_motion(ds.sites, seed=0)
    phen = pd.DataFrame(
        {"subject": X.index, "site": ds.sites, "diagnosis": ds.y,
         "mean_fd": fd}
    )
    r1 = run_qc_report(X, phen)
    r2 = run_qc_report(X, phen)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    assert r1["motion"]["total_outliers"] == 6
    assert r1["exclusions"]["n_retained"] == 234


def test_stage_synthetic_demo_default_unchanged(tmp_path):
    """with_motion=False keeps the staged files free of motion columns."""
    stage_synthetic_demo(tmp_path / "plain", seed=0)
    phen = pd.read_csv(tmp_path / "plain" / "phenotypes.csv")
    assert list(phen.columns) == ["subject", "site", "diagnosis"]


def test_stage_synthetic_demo_with_motion(tmp_path):
    """with_motion=True plants mean_fd and records the ground truth."""
    report = stage_synthetic_demo(tmp_path / "motion", seed=0, with_motion=True)
    phen = pd.read_csv(tmp_path / "motion" / "phenotypes.csv")
    assert "mean_fd" in phen.columns
    assert report["motion"]["n_planted_outliers"] == 6
    planted = set(report["motion"]["planted_outlier_subjects"])
    detected = set(phen.loc[phen["mean_fd"] > 0.2, "subject"])
    assert planted == detected


def test_qc_script_end_to_end(tmp_path):
    """The CLI writes JSON + Markdown + SVG with a synthetic scope label."""
    data_root = tmp_path / "data"
    reports_dir = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_qc_report.py"),
            "--data-root",
            str(data_root),
            "--reports-dir",
            str(reports_dir),
            "--synthetic",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((reports_dir / "qc_report_FC.json").read_text())
    assert report["synthetic"] is True
    assert report["motion"]["available"] is True
    assert report["motion"]["total_outliers"] == 6
    md = (reports_dir / "qc_report_FC.md").read_text()
    assert "synthetic demonstration" in md
    assert "Table Q1" in md and "Table Q2" in md
    svg = (reports_dir / "qc_feature_distributions_FC.svg").read_text()
    assert svg.startswith("<svg") or svg.startswith("<?xml") or "<svg" in svg[:200]
    assert "site_0" in svg and "Synthetic demo" in svg


def test_qc_script_refuses_unstaged_root(tmp_path):
    """The CLI refuses a data root without provenance (exit 1, no output)."""
    reports_dir = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_qc_report.py"),
            "--data-root",
            str(tmp_path / "empty"),
            "--reports-dir",
            str(reports_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert not reports_dir.exists()
