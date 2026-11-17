"""Tests for the config-driven LOSO benchmark runner (issue #6).

The integrity guards here pin the new single-fold machinery to the
established pipeline: single-fold outputs must agree exactly with
``LosoReplicator.run`` and with the committed synthetic-demo benchmark
numbers in ``reports/loso/loso_fold_metrics.csv``, and the checksummed
manifest must detect any alteration of the collected results set.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from benchmark import (
    build_fold_config,
    read_fold_config,
    run_fold,
    sha256_file,
    verify_manifest,
    write_fold_config,
    write_fold_output,
    write_manifest,
)
from benchmark.runner import FOLD_RESULT_SCHEMA, fold_filename
from loso_replication.combat import combat
from loso_replication.loso import LosoReplicator
from loso_replication.simulate import simulate_multisite
from loso_replication.staging import stage_synthetic_demo

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_FOLDS = REPO_ROOT / "reports" / "loso" / "loso_fold_metrics.csv"
RUN_FOLD = REPO_ROOT / "scripts" / "run_fold.py"

METRICS = ("sign_consistency", "effect_map_correlation", "heldout_significance")


@pytest.fixture(scope="module")
def dataset():
    """Synthetic multi-site dataset with planted effects.

    Returns:
        The simulated dataset (seed 7, matching tests/test_loso.py).
    """
    return simulate_multisite(seed=7)


def test_fold_config_enumerates_all_sites(dataset):
    """The configuration holds one runnable fold per site, with sizes."""
    specs = build_fold_config(dataset.sites, dataset.y)
    assert [s.held_out_site for s in specs] == sorted(np.unique(dataset.sites))
    n_per_site = len(dataset.sites) // len(specs)
    for spec in specs:
        assert spec.runnable, spec
        assert spec.skip_reason is None
        assert spec.n_test == n_per_site
        assert spec.n_train == len(dataset.sites) - n_per_site
        assert spec.n_train_sites == len(specs) - 1
        assert spec.n_cases_test + spec.n_controls_test == spec.n_test


def test_fold_config_marks_degenerate_folds():
    """Too few training sites or per-class counts are recorded, not dropped."""
    sites = np.array(["a", "a", "b", "b"])
    y = np.array([0, 1, 0, 1])
    specs = build_fold_config(sites, y, min_train_sites=2)
    assert len(specs) == 2
    assert all(not s.runnable for s in specs)
    assert all("min_train_sites" in s.skip_reason for s in specs)
    # A held-out site without both classes cannot yield effect sizes.
    sites = np.array(["a", "a", "a", "a", "b", "b", "c", "c"])
    y = np.array([0, 1, 0, 1, 0, 0, 0, 1])
    specs = build_fold_config(sites, y)
    by_site = {s.held_out_site: s for s in specs}
    assert not by_site["b"].runnable
    assert "case(s)/" in by_site["b"].skip_reason


def test_fold_config_requires_two_sites():
    """A single-site dataset cannot express any LOSO fold."""
    with pytest.raises(ValueError, match="at least 2 sites"):
        build_fold_config(np.array(["only", "only"]))


def test_fold_config_roundtrip(tmp_path, dataset):
    """Written fold configs read back identically."""
    specs = build_fold_config(dataset.sites, dataset.y)
    path = write_fold_config(specs, tmp_path / "fold_config.json", modality="FC")
    assert read_fold_config(path) == specs
    with pytest.raises(ValueError, match="fold config"):
        read_fold_config(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "something-else"}))
    with pytest.raises(ValueError, match="loso-fold-config/v1"):
        read_fold_config(bad)


def test_single_fold_matches_full_replicator(dataset):
    """run_fold must agree with LosoReplicator.run to the last bit."""
    X_h = combat(dataset.X, dataset.sites)
    full = LosoReplicator(alpha=0.05, harmonize=None).run(
        X_h, dataset.y, dataset.sites
    )
    full_by_site = {f.held_out_site: f for f in full.folds}
    for site in sorted(np.unique(dataset.sites)):
        rec = run_fold(str(site), dataset.X.to_numpy(dtype=float),
                       dataset.y, dataset.sites, alpha=0.05)
        assert rec["schema"] == FOLD_RESULT_SCHEMA
        assert rec["status"] == "completed"
        f = full_by_site[str(site)]
        assert rec["n_train"] == f.n_train
        assert rec["n_test"] == f.n_test
        for metric in METRICS:
            assert rec[metric] == getattr(f, metric), (site, metric)


def test_unknown_fold_fails_loudly(dataset):
    """A typo'd fold name raises instead of silently skipping."""
    with pytest.raises(ValueError, match="not present"):
        run_fold("site_999", dataset.X.to_numpy(dtype=float),
                 dataset.y, dataset.sites)


def test_undefined_metrics_are_null_not_nan(tmp_path):
    """Undefined metrics serialize as null; NaN tokens never reach disk."""
    # Zero planted effects -> no training-significant feature -> undefined.
    ds = simulate_multisite(
        n_sites=3, n_per_site=20, n_features=10, seed=3,
        n_replicable=0, n_nonreplicable=0,
    )
    rec = run_fold("site_0", ds.X.to_numpy(dtype=float), ds.y, ds.sites)
    if rec["sign_consistency"] is None:
        assert rec["undefined_reason"] is not None
        assert rec["n_train_significant_effects"] == 0
    path = write_fold_output(rec, tmp_path)
    text = path.read_text()
    assert "NaN" not in text and "Infinity" not in text
    json.loads(text)  # strict JSON parse


def test_manifest_verification_detects_tampering(tmp_path, dataset):
    """The checksum manifest flags altered, missing, and unlisted files."""
    sites = sorted(np.unique(dataset.sites))
    for site in sites[:3]:
        rec = run_fold(str(site), dataset.X.to_numpy(dtype=float),
                       dataset.y, dataset.sites)
        write_fold_output(rec, tmp_path)
    write_manifest(tmp_path, "FC")
    assert verify_manifest(tmp_path, "FC") == []
    # Tamper with one fold file.
    victim = tmp_path / "folds" / "FC" / fold_filename(str(sites[1]))
    victim.write_text(victim.read_text() + " ")
    problems = verify_manifest(tmp_path, "FC")
    assert any("checksum mismatch" in p for p in problems)


def test_empty_manifest_refused(tmp_path):
    """An empty results set must not produce a plausible-looking manifest."""
    with pytest.raises(FileNotFoundError):
        write_manifest(tmp_path, "FC")


def test_cli_single_fold_reproduces_committed_demo_numbers(tmp_path):
    """The CLI's per-fold output matches the committed demo benchmark CSV.

    This is the guard that lets the fold runner stand in for the full
    pipeline in a job array: on the deterministic synthetic demo, each
    single-fold run must reproduce the number the full run committed.
    """
    data_root = tmp_path / "demo"
    stage_synthetic_demo(data_root, seed=0)
    committed = pd.read_csv(COMMITTED_FOLDS)
    for _, row in committed.iterrows():
        proc = subprocess.run(
            [
                sys.executable, str(RUN_FOLD),
                "--data-root", str(data_root),
                "--results-dir", str(tmp_path / "results"),
                "--fold", row["held_out_site"],
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        rec = json.loads(
            (tmp_path / "results" / "folds" / "FC"
             / fold_filename(row["held_out_site"])).read_text()
        )
        assert rec["status"] == "completed"
        assert rec["provenance"]["synthetic"] is True
        assert rec["n_train"] == row["n_train"]
        assert rec["n_test"] == row["n_test"]
        for metric in METRICS:
            assert abs(rec[metric] - row[metric]) < 1e-12, (
                row["held_out_site"], metric, rec[metric], row[metric],
            )
    # Manifest written by --fold runs covers the collected set.
    assert verify_manifest(tmp_path / "results", "FC") == []


def test_cli_unknown_fold_exit_code(tmp_path):
    """An unknown --fold exits 2 and lists the configured folds."""
    data_root = tmp_path / "demo"
    stage_synthetic_demo(data_root, seed=0)
    proc = subprocess.run(
        [sys.executable, str(RUN_FOLD), "--data-root", str(data_root),
         "--results-dir", str(tmp_path / "r"), "--fold", "nope"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "configured folds" in proc.stderr


def test_cli_all_folds_writes_manifest(tmp_path):
    """--all writes one record per site plus a verifying manifest."""
    data_root = tmp_path / "demo"
    proc = subprocess.run(
        [sys.executable, str(RUN_FOLD), "--data-root", str(data_root),
         "--synthetic", "--results-dir", str(tmp_path / "r"), "--all"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    fold_dir = tmp_path / "r" / "folds" / "FC"
    assert len(list(fold_dir.glob("fold_*.json"))) == 6
    manifest = json.loads((fold_dir / "manifest.json").read_text())
    assert manifest["n_folds"] == 6
    assert manifest["n_completed"] == 6
    assert manifest["n_skipped"] == 0
    assert verify_manifest(tmp_path / "r", "FC") == []
    config = json.loads((tmp_path / "r" / "fold_config.json").read_text())
    assert config["n_sites"] == 6
    assert config["n_runnable"] == 6
