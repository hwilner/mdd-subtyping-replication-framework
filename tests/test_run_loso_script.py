"""End-to-end checks on scripts/run_loso.py.

These drive the CLI the way a user does, because the defect they guard is
about what the script *records*, which unit tests of the library cannot see.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_LOSO = REPO_ROOT / "scripts" / "run_loso.py"
PREPARE = REPO_ROOT / "scripts" / "prepare_rest_meta_mdd.py"


def _run(script, *args):
    """Run one of the repository CLI scripts.

    Args:
        script: Path to the script to execute.
        *args: Command-line arguments for the script.

    Returns:
        subprocess.CompletedProcess: The finished process.
    """
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_benchmark_demo_records_synthetic_provenance(tmp_path):
    """`make benchmark-demo` must record the run as synthetic.

    The Makefile stages synthetic data in one step and runs the benchmark in a
    second, so run_loso.py is invoked *without* --synthetic. That flag only
    decides whether the script writes demo data, so using it as the recorded
    provenance labelled the demo run as real data -- exactly the confusion the
    DUA forbids in a repository that commits its benchmark outputs.

    Args:
        tmp_path: tmp path.
    """
    data_root = tmp_path / "demo"
    reports = tmp_path / "reports"

    staged = _run(PREPARE, "--data-root", str(data_root), "--synthetic")
    assert staged.returncode == 0, staged.stderr
    assert json.loads((data_root / "STAGING_REPORT.json").read_text())["synthetic"] is True

    # No --synthetic here: this mirrors the Makefile's two-step demo.
    run = _run(RUN_LOSO, "--data-root", str(data_root), "--reports-dir", str(reports))
    assert run.returncode == 0, run.stderr

    summary = json.loads((reports / "loso_run_summary.json").read_text())
    assert summary["synthetic"] is True, (
        "synthetic demo data was recorded as real data in the run summary"
    )
    assert summary["provenance_source"] == "STAGING_REPORT.json"
    assert "SYNTHETIC (demo)" in run.stdout


def test_run_summary_reports_fold_coverage(tmp_path):
    """The run summary must say how many folds each aggregate covers.

    Args:
        tmp_path: tmp path.
    """
    data_root = tmp_path / "demo"
    reports = tmp_path / "reports"
    assert _run(RUN_LOSO, "--data-root", str(data_root), "--synthetic",
                "--reports-dir", str(reports)).returncode == 0

    summary = json.loads((reports / "loso_run_summary.json").read_text())
    assert summary["n_folds"] == summary["n_sites"] == 6
    assert summary["n_sites_skipped"] == 0
    assert summary["n_folds_sign_consistency_defined"] == summary["n_folds"]
    assert summary["n_folds_heldout_significance_defined"] == summary["n_folds"]
    assert 0.0 <= summary["mean_sign_consistency"] <= 1.0


def test_run_refuses_to_run_without_provenance(tmp_path):
    """Unstaged data must stop the benchmark instead of guessing provenance.

    Args:
        tmp_path: tmp path.
    """
    data_root = tmp_path / "demo"
    data_root.mkdir()
    run = _run(RUN_LOSO, "--data-root", str(data_root),
               "--reports-dir", str(tmp_path / "reports"))
    assert run.returncode == 1
    assert "provenance" in run.stderr.lower() or "Cannot run benchmark" in run.stderr
    assert not (tmp_path / "reports" / "loso_run_summary.json").exists()


def test_unsupported_modality_is_rejected_by_the_cli(tmp_path):
    """A modality the loaders cannot read must fail fast, not mid-run.

    Args:
        tmp_path: tmp path.
    """
    run = _run(RUN_LOSO, "--data-root", str(tmp_path), "--modality", "EEG")
    assert run.returncode == 2, "argparse should reject the bad modality"
    assert "invalid choice" in run.stderr


CHECK_REPRO = REPO_ROOT / "scripts" / "check_demo_reproducibility.py"
COMMITTED_SUMMARY = REPO_ROOT / "reports" / "loso" / "loso_run_summary.json"


def test_committed_demo_report_still_reproduces():
    """The committed demo numbers must match a fresh run of the current code.

    docs/METHODS.md quotes these figures, so if the default path drifts the
    documentation goes stale and nothing else would notice.

    Returns:
        None.
    """
    run = _run(CHECK_REPRO)
    assert run.returncode == 0, f"committed demo report drifted:\n{run.stdout}\n{run.stderr}"


def test_reproducibility_check_detects_a_drifted_number():
    """The check must fail when a committed number no longer reproduces.

    A guard that cannot fail is worse than no guard, because it looks like
    coverage. This perturbs one committed figure, confirms the check reports
    the drift, and restores the file.

    Returns:
        None.
    """
    original = COMMITTED_SUMMARY.read_text()
    try:
        drifted = json.loads(original)
        drifted["mean_sign_consistency"] = drifted["mean_sign_consistency"] + 0.25
        COMMITTED_SUMMARY.write_text(json.dumps(drifted, indent=2) + "\n")

        run = _run(CHECK_REPRO)
        assert run.returncode == 1, "the check passed a drifted committed number"
        assert "no longer reproduces" in run.stderr
        assert "mean_sign_consistency" in run.stderr
    finally:
        COMMITTED_SUMMARY.write_text(original)

    # Restoring the file must make the check pass again.
    assert _run(CHECK_REPRO).returncode == 0
