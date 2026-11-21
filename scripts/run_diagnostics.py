#!/usr/bin/env python
"""Pre/post-harmonization batch-effect diagnostics report (issue #10).

Compares site-related signal in the staged feature matrix before and
after ComBat harmonization — per-feature site eta^2, cross-validated
site-classification accuracy, between-site mean spread — and checks that
the case-control effect map is preserved. Writes a JSON report plus a
captioned Markdown summary under ``reports/diagnostics/``.

This command computes diagnostics only; it never changes the
harmonization method, and real-data outputs must respect the DUA terms.

Usage:

    # Real staged data (post-DUA):
    python scripts/run_diagnostics.py --data-root /path/to/rest-meta-mdd

    # Demo on synthetic data (no DUA needed):
    python scripts/run_diagnostics.py --data-root data/demo --synthetic
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loso_replication.diagnostics import run_batch_diagnostics  # noqa: E402
from loso_replication.staging import (  # noqa: E402
    StagingError,
    load_staged_dataset,
    read_synthetic_flag,
    stage_synthetic_demo,
)


def render_markdown(report: dict, synthetic: bool) -> str:
    """Render the diagnostics report as a captioned Markdown summary.

    Args:
        report: The report dict from :func:`run_batch_diagnostics` plus
            provenance fields.
        synthetic: Whether the underlying data are the synthetic demo
            dataset; controls the scope label wording.

    Returns:
        str: Markdown with one captioned table per diagnostics block.
    """
    scope = (
        "synthetic demonstration — validates the diagnostics machinery, not an MDD finding"
        if synthetic
        else "REST-meta-MDD Phase II data — handle per DUA terms"
    )
    pre, post = report["pre"], report["post"]
    bio = report["biological_preservation"]
    lines = [
        "# Batch-effect diagnostics (pre/post ComBat)",
        "",
        f"Scope: {scope}. Data root `{report['data_root']}`, modality "
        f"{report['modality']}; harmonization: {report['harmonization']}.",
        "",
        "**Table D1. Site-signal diagnostics before vs. after harmonization.** "
        "Site eta^2 is the per-feature fraction of variance explained by site; "
        "site classification is the cross-validated accuracy of predicting site "
        "from the features (chance = largest site fraction); site-mean spread is "
        "the SD of per-site feature means. All three should fall after ComBat.",
        "",
        "| Diagnostic | Pre-ComBat | Post-ComBat |",
        "|---|---:|---:|",
        f"| Site eta^2 (mean over features) | {pre['eta_squared_mean']:.4f} | {post['eta_squared_mean']:.4f} |",
        f"| Site eta^2 (max over features) | {pre['eta_squared_max']:.4f} | {post['eta_squared_max']:.4f} |",
        f"| Site classification accuracy | {pre['site_classification']['accuracy']:.4f} | {post['site_classification']['accuracy']:.4f} |",
        f"| Chance (majority site fraction) | {pre['site_classification']['chance_majority']:.4f} | {post['site_classification']['chance_majority']:.4f} |",
        f"| Site-mean spread (mean over features) | {pre['site_mean_spread']['mean']:.4f} | {post['site_mean_spread']['mean']:.4f} |",
        "",
        "**Table D2. Biological-signal preservation.** The case-control Cohen's d "
        "effect map before vs. after harmonization; a high correlation and few "
        "sign flips mean ComBat removed batch signal without removing the "
        "biological covariate signal.",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| Effect-map correlation (pre vs. post) | {bio['effect_map_correlation']:.4f} |",
        f"| Mean |d| pre-ComBat | {bio['mean_abs_d_pre']:.4f} |",
        f"| Mean |d| post-ComBat | {bio['mean_abs_d_post']:.4f} |",
        f"| Sign flips | {bio['sign_flips']} / {bio['n_features']} |",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    """Run the batch-effect diagnostics and write the reports.

    Returns:
        int: Exit code — 0 on success, 1 if the staged data cannot be
        loaded or its provenance cannot be verified.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--modality", default="FC", choices=["FC", "ALFF", "ReHo"])
    ap.add_argument("--reports-dir", default="reports/diagnostics")
    ap.add_argument("--synthetic", action="store_true",
                    help="stage a synthetic demo dataset first (no DUA needed)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.synthetic:
        stage_synthetic_demo(args.data_root, seed=args.seed)

    try:
        synthetic = read_synthetic_flag(args.data_root)
        X, y, sites = load_staged_dataset(args.data_root, args.modality)
    except StagingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    report = run_batch_diagnostics(X, y, sites, seed=args.seed)
    report["data_root"] = str(args.data_root)
    report["modality"] = args.modality
    report["synthetic"] = synthetic
    report["seed"] = args.seed

    out = Path(args.reports_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"batch_effect_diagnostics_{args.modality}.json"
    md_path = out / f"batch_effect_diagnostics_{args.modality}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(render_markdown(report, synthetic))
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
