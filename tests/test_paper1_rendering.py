"""Tests for the Paper 1 rendering scripts (issue #7).

The scripts render committed results artifacts into paper tables/figures;
these tests pin the regeneration contract — byte-deterministic output,
numbers matching the committed artifacts, and a committed-output freshness
check analogous to ``scripts/check_demo_reproducibility.py``.
"""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKE_TABLES = REPO_ROOT / "reports" / "paper1" / "make_tables.py"
MAKE_FIGURES = REPO_ROOT / "reports" / "paper1" / "make_figures.py"
COMMITTED_DIR = REPO_ROOT / "reports" / "paper1"

TABLE_FILES = (
    "table1_run_summary.md",
    "table2_fold_metrics.md",
    "table3_aggregate_metrics.md",
)
FIGURE_FILES = ("fig2_loso_metrics_by_site_demo.svg", "fig2_caption.md")


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a rendering script.

    Args:
        script: The script path.
        *args: Extra command-line arguments.

    Returns:
        subprocess.CompletedProcess: The finished process.
    """
    return subprocess.run(
        [sys.executable, str(script), *args], capture_output=True, text=True
    )


def test_tables_deterministic(tmp_path):
    """Two runs into separate directories produce identical bytes."""
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    for out in (out_a, out_b):
        proc = _run(MAKE_TABLES, "--out-dir", str(out))
        assert proc.returncode == 0, proc.stderr
    for name in TABLE_FILES:
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes()


def test_figures_deterministic(tmp_path):
    """The SVG figure regenerates byte-identically."""
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    for out in (out_a, out_b):
        proc = _run(MAKE_FIGURES, "--out-dir", str(out))
        assert proc.returncode == 0, proc.stderr
    for name in FIGURE_FILES:
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes()


def test_tables_match_committed_artifacts(tmp_path):
    """Rendered numbers match the committed JSON/CSV sources exactly."""
    proc = _run(MAKE_TABLES, "--out-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(
        (REPO_ROOT / "reports" / "loso" / "loso_run_summary.json").read_text()
    )
    folds = pd.read_csv(REPO_ROOT / "reports" / "loso" / "loso_fold_metrics.csv")
    t1 = (tmp_path / "table1_run_summary.md").read_text()
    assert f"| Subjects | {summary['n_subjects']} |" in t1
    assert "| Synthetic data | true |" in t1
    t2 = (tmp_path / "table2_fold_metrics.md").read_text()
    for _, row in folds.iterrows():
        assert f"| {row['held_out_site']} |" in t2
    t3 = (tmp_path / "table3_aggregate_metrics.md").read_text()
    assert f"{summary['mean_sign_consistency']:.3f}" in t3
    assert f"{summary['mean_effect_map_correlation']:.3f}" in t3
    assert f"{summary['mean_heldout_significance']:.3f}" in t3
    # The synthetic scope label must be present on every table.
    for name in TABLE_FILES:
        assert "not an MDD finding" in (tmp_path / name).read_text()


def test_tables_refuse_stale_artifacts(tmp_path):
    """A JSON/CSV inconsistency aborts rendering rather than rendering lies."""
    loso = tmp_path / "loso"
    loso.mkdir()
    src = REPO_ROOT / "reports" / "loso"
    summary = json.loads((src / "loso_run_summary.json").read_text())
    summary["mean_sign_consistency"] = 0.999  # no longer matches the CSV
    (loso / "loso_run_summary.json").write_text(json.dumps(summary))
    (loso / "loso_fold_metrics.csv").write_bytes(
        (src / "loso_fold_metrics.csv").read_bytes()
    )
    proc = _run(MAKE_TABLES, "--loso-dir", str(loso), "--out-dir", str(tmp_path / "o"))
    assert proc.returncode != 0
    assert "Artifact mismatch" in proc.stderr
    assert not (tmp_path / "o" / "table1_run_summary.md").exists()


def test_figure2_wellformed_and_captioned(tmp_path):
    """The SVG parses, carries its caption, and covers every demo site."""
    proc = _run(MAKE_FIGURES, "--out-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    svg = (tmp_path / "fig2_loso_metrics_by_site_demo.svg").read_text()
    ET.fromstring(svg)  # well-formed XML
    assert "<desc>" in svg and "not an MDD finding" in svg
    folds = pd.read_csv(REPO_ROOT / "reports" / "loso" / "loso_fold_metrics.csv")
    for site in folds["held_out_site"]:
        assert f">{site}<" in svg
    caption = (tmp_path / "fig2_caption.md").read_text()
    assert "Figure 2" in caption and "issue #14" in caption


def test_committed_outputs_fresh(tmp_path):
    """The committed reports/paper1/ outputs match regeneration exactly.

    This is the staleness guard: if the committed artifacts or the scripts
    change, the committed rendered outputs must be regenerated in the same
    change, or this test fails.
    """
    proc = _run(MAKE_TABLES, "--out-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    proc = _run(MAKE_FIGURES, "--out-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    for name in TABLE_FILES + FIGURE_FILES:
        committed = COMMITTED_DIR / name
        assert committed.exists(), f"{committed} missing"
        assert committed.read_bytes() == (tmp_path / name).read_bytes(), (
            f"{name} is stale; regenerate with `make paper1-demo`"
        )
