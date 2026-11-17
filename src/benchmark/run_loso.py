"""CLI: run a single LOSO fold (or all folds) end to end.

Usage (package installed, e.g. ``pip install -e .``):

    # Single fold on staged real data (post-DUA):
    python -m benchmark.run_loso --data-root /path/to/rest-meta-mdd --fold site_03

    # Single fold on the synthetic demo (no DUA needed):
    python -m benchmark.run_loso --data-root data/demo --synthetic --fold site_0

    # All folds:
    python -m benchmark.run_loso --data-root data/demo --all

Each fold writes ``<results-dir>/folds/<modality>/fold_<site>.json`` and
the results directory gains a ``fold_config.json`` plus a checksummed
``manifest.json``. A thin wrapper is available as ``scripts/run_fold.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from loso_replication.io import DataAccessError
from loso_replication.staging import (
    StagingError,
    load_staged_dataset,
    read_synthetic_flag,
    stage_synthetic_demo,
)

from .folds import build_fold_config, write_fold_config
from .runner import run_fold, write_fold_output, write_manifest


def main(argv: list[str] | None = None) -> int:
    """Run one or all LOSO folds and write checksummed per-fold outputs.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        int: Exit code — 0 on success, 1 if the staged data cannot be
        loaded or its provenance verified, 2 if a requested fold is not in
        the fold configuration.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--modality", default="FC", choices=["FC", "ALFF", "ReHo"])
    ap.add_argument("--results-dir", default="reports/loso")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--min-train-sites", type=int, default=2)
    ap.add_argument("--fold", default=None,
                    help="held-out site to evaluate (one fold)")
    ap.add_argument("--all", action="store_true",
                    help="run every fold in the configuration")
    ap.add_argument("--synthetic", action="store_true",
                    help="stage a synthetic demo dataset first (no DUA needed)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    if not args.all and args.fold is None:
        ap.error("specify --fold SITE or --all")

    if args.synthetic:
        stage_synthetic_demo(args.data_root, seed=args.seed)

    try:
        X, y, sites = load_staged_dataset(args.data_root, args.modality)
        # Provenance comes from the staging report, never from --synthetic;
        # see scripts/run_loso.py for why the distinction matters (DUA).
        is_synthetic = read_synthetic_flag(args.data_root)
    except (StagingError, DataAccessError) as e:
        print(f"Cannot run benchmark: {e}", file=sys.stderr)
        return 1

    X_arr = X.to_numpy(dtype=float)
    specs = build_fold_config(sites, y, min_train_sites=args.min_train_sites)
    config_path = write_fold_config(
        specs,
        Path(args.results_dir) / "fold_config.json",
        min_train_sites=args.min_train_sites,
        modality=args.modality,
    )
    by_site = {s.held_out_site: s for s in specs}

    if args.all:
        requested = [s.held_out_site for s in specs]
    else:
        if args.fold not in by_site:
            print(
                f"Unknown fold {args.fold!r}; configured folds: "
                f"{sorted(by_site)}",
                file=sys.stderr,
            )
            return 2
        requested = [args.fold]

    print(
        f"Loaded {X_arr.shape[0]} subjects x {X_arr.shape[1]} features from "
        f"{len(specs)} sites ({args.modality}); data is "
        f"{'SYNTHETIC (demo)' if is_synthetic else 'real (post-DUA)'}"
    )
    print(f"Fold configuration ({len(specs)} folds) -> {config_path}")

    provenance = {
        "data_root": str(args.data_root),
        "synthetic": is_synthetic,
        "source": "STAGING_REPORT.json",
    }
    for held in requested:
        record = run_fold(
            held,
            X_arr,
            y,
            sites,
            alpha=args.alpha,
            min_train_sites=args.min_train_sites,
            modality=args.modality,
            provenance=provenance,
        )
        out = write_fold_output(record, args.results_dir)
        if record["status"] == "completed":
            print(
                f"fold {held}: sign={record['sign_consistency']:.3f} "
                f"corr={record['effect_map_correlation']:.3f} "
                f"heldout_sig={record['heldout_significance']:.3f} -> {out}"
            )
        else:
            print(f"fold {held}: SKIPPED ({record['skip_reason']}) -> {out}")

    manifest = write_manifest(args.results_dir, args.modality)
    print(f"Manifest -> {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
