#!/usr/bin/env python
"""Stage REST-meta-MDD Phase II derivatives for the LOSO benchmark.

Real data require an approved DUA (see docs/DATA_ACCESS.md) and must be
placed in a local data root outside the repository with the layout:

    $DATA_ROOT/
      phenotypes.csv      # subject, site, diagnosis (1=MDD, 0=HC)
      features_fc.csv     # subjects x features (functional connectivity)
      features_alff.csv   # subjects x features
      features_reho.csv   # subjects x features

This script checks the layout and file integrity and writes
``STAGING_REPORT.json`` into the data root. With ``--synthetic`` it
instead writes a small synthetic dataset in the same layout so the full
prepare -> benchmark path can be exercised without the DUA data.

Usage
-----
    python scripts/prepare_rest_meta_mdd.py --data-root /path/to/rest-meta-mdd
    python scripts/prepare_rest_meta_mdd.py --data-root data/demo --synthetic
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loso_replication.staging import (  # noqa: E402
    StagingError,
    stage_synthetic_demo,
    validate_staged,
    write_staging_report,
)


def main() -> int:
    """Main.

    Returns:
        int: the result.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", required=True,
                    help="directory holding the staged REST-meta-MDD files")
    ap.add_argument("--modalities", default="FC",
                    help="comma-separated subset of FC,ALFF,ReHo to validate")
    ap.add_argument("--synthetic", action="store_true",
                    help="write a synthetic demo dataset instead of validating real data")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    modalities = tuple(m.strip() for m in args.modalities.split(",") if m.strip())

    if args.synthetic:
        report = stage_synthetic_demo(args.data_root, seed=args.seed)
        print(f"Synthetic demo staged in {args.data_root}: "
              f"{report['n_subjects']} subjects, {report['n_sites']} sites, "
              f"{report['modalities']['FC']['n_features']} features")
        return 0

    try:
        report = validate_staged(args.data_root, modalities=modalities)
    except StagingError as e:
        print(f"STAGING FAILED: {e}", file=sys.stderr)
        return 1
    report["synthetic"] = False
    write_staging_report(args.data_root, report)
    print(json.dumps(report, indent=2))
    print("Staging OK. Run the benchmark with: "
          f"python scripts/run_loso.py --data-root {args.data_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
