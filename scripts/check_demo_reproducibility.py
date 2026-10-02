#!/usr/bin/env python
"""Check that the committed demo benchmark outputs still reproduce.

The committed files under ``reports/loso/`` are the only benchmark numbers in
this repository, and ``docs/METHODS.md`` quotes them. If the default code path
drifts, those numbers and the documentation go stale silently — nothing else in
the pipeline would notice. This script regenerates the synthetic demo into a
scratch directory and compares the result against the committed report.

It never writes inside the repository, so it is safe to run on a dirty tree
(and in CI). Run it with ``--update`` to refresh the committed outputs after an
intentional change to the default path.

Usage
-----
    python scripts/check_demo_reproducibility.py
    python scripts/check_demo_reproducibility.py --update
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
#: Keys compared against the committed report. Provenance and fold-coverage
#: keys added later are deliberately excluded: they describe the run, not the
#: benchmark numbers the documentation cites.
COMPARED_KEYS = (
    "n_subjects",
    "n_features",
    "n_sites",
    "alpha",
    "synthetic",
    "mean_sign_consistency",
    "mean_effect_map_correlation",
    "mean_heldout_significance",
)


def _run(*argv: str) -> None:
    """Run a repository script, raising on failure.

    Args:
        *argv: Script name followed by its arguments.

    Raises:
        subprocess.CalledProcessError: If the script exits non-zero.
    """
    subprocess.run([sys.executable, *argv], check=True, cwd=REPO_ROOT, capture_output=True)


def regenerate(data_root: Path, reports_dir: Path) -> dict:
    """Stage the synthetic demo and run the benchmark into scratch directories.

    Args:
        data_root: Scratch directory for the staged demo data.
        reports_dir: Scratch directory for the benchmark outputs.

    Returns:
        dict: The freshly generated run summary.
    """
    _run("scripts/prepare_rest_meta_mdd.py", "--data-root", str(data_root), "--synthetic")
    _run("scripts/run_loso.py", "--data-root", str(data_root), "--reports-dir", str(reports_dir))
    return json.loads((reports_dir / "loso_run_summary.json").read_text())


def main() -> int:
    """Compare a fresh demo run against the committed run summary.

    Returns:
        int: 0 if the committed outputs reproduce, 1 on drift or if no
        committed summary exists to compare against.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--update",
        action="store_true",
        help="overwrite the committed report with the freshly generated one",
    )
    args = ap.parse_args()

    committed_path = REPO_ROOT / "reports" / "loso" / "loso_run_summary.json"

    if args.update:
        # Regenerate exactly the way `make benchmark-demo` does — relative
        # paths, as the Makefile passes them — so the committed report keeps
        # its canonical `data_root` of "data/demo" rather than recording a
        # machine-specific absolute path that means nothing to a reader.
        fresh = regenerate(Path("data/demo"), Path("reports/loso"))
        committed_path.parent.mkdir(parents=True, exist_ok=True)
        committed_path.write_text(json.dumps(fresh, indent=2) + "\n")
        print(f"Updated {committed_path.relative_to(REPO_ROOT)}")
        return 0

    # Checking runs entirely in scratch space so it never dirties the tree.
    with tempfile.TemporaryDirectory() as tmp:
        fresh = regenerate(Path(tmp) / "demo", Path(tmp) / "reports")

    if not committed_path.exists():
        print(f"No committed summary at {committed_path} to compare against.", file=sys.stderr)
        return 1
    committed = json.loads(committed_path.read_text())

    drift = {
        key: (committed.get(key), fresh.get(key))
        for key in COMPARED_KEYS
        if key in committed and committed[key] != fresh.get(key)
    }
    for key in COMPARED_KEYS:
        if key in committed:
            print(f"  {key}: committed={committed[key]!r} fresh={fresh.get(key)!r}")

    if drift:
        print(
            "The committed demo report no longer reproduces. Either the default "
            "code path changed, or the committed numbers are stale. Review the "
            "diff below; if the change was intended, refresh the outputs with "
            "`python scripts/check_demo_reproducibility.py --update` and update "
            f"the figures quoted in docs/METHODS.md.\nDrift (committed -> fresh): "
            f"{json.dumps(drift, indent=2)}",
            file=sys.stderr,
        )
        return 1

    print(f"Committed demo report reproduces exactly ({len(COMPARED_KEYS)} keys checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
