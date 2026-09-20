#!/usr/bin/env python
"""One-command LOSO replication benchmark on staged data.

Runs the moment data are staged (see scripts/prepare_rest_meta_mdd.py):
ComBat-harmonizes the feature matrix, runs the leave-one-site-out
replication benchmark, and writes per-fold and aggregate metrics to
``reports/loso/`` (small CSV/JSON, safe to commit for synthetic runs;
real-data outputs must respect the DUA terms).

Usage
-----
    # Real staged data (post-DUA):
    python scripts/run_loso.py --data-root /path/to/rest-meta-mdd

    # Demo on synthetic data (no DUA needed):
    python scripts/run_loso.py --data-root data/demo --synthetic
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from loso_replication.combat import combat  # noqa: E402
from loso_replication.io import DataAccessError  # noqa: E402
from loso_replication.loso import LosoReplicator  # noqa: E402
from loso_replication.staging import (  # noqa: E402
    StagingError,
    load_staged_dataset,
    stage_synthetic_demo,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--modality", default="FC", choices=["FC", "ALFF", "ReHo"])
    ap.add_argument("--reports-dir", default="reports/loso")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--synthetic", action="store_true",
                    help="stage a synthetic demo dataset first (no DUA needed)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.synthetic:
        stage_synthetic_demo(args.data_root, seed=args.seed)

    try:
        X, y, sites = load_staged_dataset(args.data_root, args.modality)
    except (StagingError, DataAccessError) as e:
        print(f"Cannot run benchmark: {e}", file=sys.stderr)
        return 1

    print(f"Loaded {X.shape[0]} subjects x {X.shape[1]} features "
          f"from {len(np.unique(sites))} sites ({args.modality})")

    rep = LosoReplicator(alpha=args.alpha, harmonize=None)
    X_h = combat(X, sites)
    result = rep.run(X_h, y, sites)

    out = Path(args.reports_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = result.summary()
    summary.to_csv(out / "loso_fold_metrics.csv", index=False)
    run_summary = {
        "data_root": str(args.data_root),
        "modality": args.modality,
        "synthetic": bool(args.synthetic),
        "n_subjects": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "n_sites": int(len(np.unique(sites))),
        "alpha": args.alpha,
        "harmonization": "combat (built-in empirical Bayes)",
        "mean_sign_consistency": result.mean_sign_consistency,
        "mean_effect_map_correlation": result.mean_effect_map_correlation,
        "mean_heldout_significance": result.mean_heldout_significance,
    }
    (out / "loso_run_summary.json").write_text(json.dumps(run_summary, indent=2))
    print(summary.to_string(index=False))
    print(f"\nMean sign consistency: {result.mean_sign_consistency:.3f}")
    print(f"Mean effect-map correlation: {result.mean_effect_map_correlation:.3f}")
    print(f"Mean held-out significance: {result.mean_heldout_significance:.3f}")
    print(f"Wrote {out}/loso_fold_metrics.csv and loso_run_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
