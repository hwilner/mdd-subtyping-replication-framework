#!/usr/bin/env python
"""Motion and preprocessing QC report on the staged inputs (issue #13).

Computes input QC for the harmonization/benchmark inputs: motion outliers
and exclusion counts per site, plus per-site feature-distribution
summaries. Writes a JSON report, a captioned Markdown summary, and a
deterministic SVG distribution figure under ``reports/qc/``.

Scope boundary (from the issue): QC of inputs only — this script never
touches the harmonization method, and pre/post-harmonization batch-effect
diagnostics are a separate sub-task (``scripts/run_diagnostics.py``). If
the staged phenotypes carry no motion column, the motion block is reported
as unavailable rather than estimated; real-data outputs must respect the
DUA terms.

Usage:

    # Real staged data (post-DUA):
    python scripts/run_qc_report.py --data-root /path/to/rest-meta-mdd

    # Demo on synthetic data (no DUA needed; plants a mean_fd column with
    # known motion outliers so the full report path is exercised):
    python scripts/run_qc_report.py --data-root data/demo --synthetic
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loso_replication.qc import (  # noqa: E402
    DEFAULT_MOTION_THRESHOLD_MM,
    render_feature_distribution_svg,
    run_qc_report,
)
from loso_replication.staging import (  # noqa: E402
    StagingError,
    load_staged_dataset,
    read_synthetic_flag,
    stage_synthetic_demo,
)
from loso_replication.io import load_phenotypes  # noqa: E402


def render_markdown(report: dict, synthetic: bool) -> str:
    """Render the QC report as a captioned Markdown summary.

    Args:
        report: The report dict from :func:`run_qc_report` plus provenance
            fields.
        synthetic: Whether the underlying data are the synthetic demo
            dataset; controls the scope label wording.

    Returns:
        str: Markdown with one captioned table per QC block.
    """
    scope = (
        "synthetic demonstration — validates the QC machinery, not an MDD finding"
        if synthetic
        else "REST-meta-MDD Phase II data — handle per DUA terms"
    )
    motion = report["motion"]
    excl = report["exclusions"]
    dist = report["feature_distributions"]["per_site"]
    lines = [
        "# Motion and preprocessing QC report (inputs only)",
        "",
        f"Scope: {scope}. Data root `{report['data_root']}`, modality "
        f"{report['modality']}.",
        "",
    ]
    if motion["available"]:
        lines += [
            f"**Table Q1. Motion outliers and exclusion counts per site.** "
            f"A subject is excluded when its mean framewise displacement "
            f"(`{motion['column']}`) exceeds {motion['threshold_mm']} mm "
            f"(declared default; pre-registered value for the real run may "
            f"differ) or its feature row contains a non-finite value. "
            f"Offending subject IDs are listed in the JSON report.",
            "",
            "| Site | N | Motion outliers | Data exclusions | Excluded | Retained |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for site in sorted(excl["per_site"]):
            e = excl["per_site"][site]
            lines.append(
                f"| {site} | {e['n_total']} | {e['n_motion_excluded']} | "
                f"{e['n_data_excluded']} | {e['n_excluded']} | "
                f"{e['n_retained']} |"
            )
        lines += [
            f"| **Total** | **{excl['n_total']}** | "
            f"**{motion['total_outliers']}** | "
            f"**{sum(e['n_data_excluded'] for e in excl['per_site'].values())}** "
            f"| **{excl['n_excluded']}** | **{excl['n_retained']}** |",
            "",
        ]
    else:
        lines += [
            "**Motion QC: unavailable.** "
            f"{motion['reason']}. No motion exclusions were applied and none "
            "are estimated; exclusion counts below reflect data quality only.",
            "",
            "| Site | N | Data exclusions | Excluded | Retained |",
            "|---|---:|---:|---:|---:|",
        ]
        for site in sorted(excl["per_site"]):
            e = excl["per_site"][site]
            lines.append(
                f"| {site} | {e['n_total']} | {e['n_data_excluded']} | "
                f"{e['n_excluded']} | {e['n_retained']} |"
            )
        lines.append("")
    lines += [
        "**Table Q2. Per-site pooled feature-value distribution.** "
        "Five-number summary, mean, and SD of all feature values pooled "
        "over subjects per site (a distribution QC view: scanner scaling "
        "shifts show up here). The matching figure is "
        f"`qc_feature_distributions_{report['modality']}.svg`.",
        "",
        "| Site | Mean | SD | Min | Q1 | Median | Q3 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for site in sorted(dist):
        d = dist[site]
        lines.append(
            f"| {site} | {d['mean']:.4f} | {d['sd']:.4f} | {d['min']:.4f} "
            f"| {d['q1']:.4f} | {d['median']:.4f} | {d['q3']:.4f} "
            f"| {d['max']:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the input-QC report and write the outputs.

    Returns:
        int: Exit code — 0 on success, 1 if the staged data cannot be
        loaded or its provenance cannot be verified.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--modality", default="FC", choices=["FC", "ALFF", "ReHo"])
    ap.add_argument("--reports-dir", default="reports/qc")
    ap.add_argument("--synthetic", action="store_true",
                    help="stage a synthetic demo dataset first (no DUA needed); "
                    "plants a mean_fd column with known motion outliers")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--motion-threshold", type=float,
                    default=DEFAULT_MOTION_THRESHOLD_MM,
                    help="mean-FD exclusion threshold in mm "
                    "(default: %(default)s, a declared standard value)")
    ap.add_argument("--motion-column", default=None,
                    help="explicit FD column name (default: auto-detect)")
    args = ap.parse_args()

    if args.synthetic:
        stage_synthetic_demo(args.data_root, seed=args.seed, with_motion=True)

    try:
        synthetic = read_synthetic_flag(args.data_root)
        X, y, sites = load_staged_dataset(args.data_root, args.modality)
        phen = load_phenotypes(args.data_root)
    except StagingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    report = run_qc_report(
        X, phen,
        threshold_mm=args.motion_threshold,
        motion_column=args.motion_column,
    )
    report["data_root"] = str(args.data_root)
    report["modality"] = args.modality
    report["synthetic"] = synthetic
    report["seed"] = args.seed

    scope = (
        "Synthetic demo — QC machinery validation, not an MDD finding"
        if synthetic
        else "REST-meta-MDD Phase II — handle per DUA terms"
    )
    if report["motion"]["available"]:
        threshold_note = (
            f"Exclusion rule: mean FD > "
            f"{report['motion']['threshold_mm']} mm or non-finite features."
        )
    else:
        threshold_note = (
            "No motion column in input; exclusion rule: non-finite "
            "features only."
        )

    out = Path(args.reports_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"qc_report_{args.modality}.json"
    md_path = out / f"qc_report_{args.modality}.md"
    svg_path = out / f"qc_feature_distributions_{args.modality}.svg"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(render_markdown(report, synthetic))
    svg_path.write_text(
        render_feature_distribution_svg(
            report["feature_distributions"], args.modality, scope,
            threshold_note,
        )
    )
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"wrote {svg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
