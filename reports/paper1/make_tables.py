#!/usr/bin/env python
"""Render the Paper 1 results tables from committed artifacts (issue #7).

Reads only committed results artifacts — ``reports/loso/loso_run_summary.json``
and ``reports/loso/loso_fold_metrics.csv`` — and writes the captioned
markdown tables quoted in the paper docs. No benchmark quantity is
recomputed; the only arithmetic is an integrity check that the aggregate
means in the JSON still match the per-fold CSV (the script refuses to
write anything if they do not).

Usage:

    python reports/paper1/make_tables.py            # writes reports/paper1/
    python reports/paper1/make_tables.py --out-dir /tmp/out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOSO_DIR = REPO_ROOT / "reports" / "loso"
DEFAULT_OUT_DIR = REPO_ROOT / "reports" / "paper1"

#: Fixed interpretations for the aggregate table (same wording as
#: docs/RESULTS.md, which quotes these numbers).
INTERPRETATIONS = {
    "sign_consistency": (
        "Fraction of training-significant effects with the same direction "
        "at the held-out site"
    ),
    "effect_map_correlation": (
        "Pearson correlation between train and held-out Cohen's d maps"
    ),
    "heldout_significance": (
        "Fraction of training-significant effects that are nominally "
        "significant at the held-out site"
    ),
}

#: Every generated table carries this scope label: the committed artifacts
#: are a synthetic pipeline demonstration, not an MDD finding.
SCOPE_LABEL = (
    "*Synthetic demonstration of the benchmark pipeline — not an MDD finding. "
    "Real-data tables remain blocked on DUA access (issue #2).*"
)


def _fmt(x: float) -> str:
    """Format a metric value at three decimals.

    Args:
        x: The value to format.

    Returns:
        str: The formatted value, or an em dash for undefined entries.
    """
    return f"{x:.3f}" if pd.notna(x) else "—"


def load_artifacts(loso_dir: Path) -> tuple[dict, pd.DataFrame]:
    """Load and integrity-check the committed benchmark artifacts.

    Args:
        loso_dir: Directory holding ``loso_run_summary.json`` and
            ``loso_fold_metrics.csv``.

    Returns:
        tuple[dict, pd.DataFrame]: The run summary and per-fold metrics.

    Raises:
        SystemExit: If the aggregate means in the JSON no longer match the
            per-fold CSV (stale or edited artifacts), so a drifting results
            set can never be rendered into paper tables unnoticed.
    """
    summary = json.loads((loso_dir / "loso_run_summary.json").read_text())
    folds = pd.read_csv(loso_dir / "loso_fold_metrics.csv")
    if len(folds) != summary["n_folds"]:
        raise SystemExit(
            f"Artifact mismatch: {len(folds)} fold rows vs "
            f"n_folds={summary['n_folds']} in run summary."
        )
    for metric in INTERPRETATIONS:
        defined = folds[metric].dropna()
        mean = defined.mean()
        committed = summary[f"mean_{metric}"]
        if abs(mean - committed) > 1e-12:
            raise SystemExit(
                f"Artifact mismatch: recomputed mean {metric}={mean!r} vs "
                f"committed {committed!r}; refusing to render stale tables."
            )
        if len(defined) != summary[f"n_folds_{metric}_defined"]:
            raise SystemExit(
                f"Artifact mismatch: {len(defined)} defined {metric} folds vs "
                f"committed {summary[f'n_folds_{metric}_defined']}."
            )
    return summary, folds


def render_table1(summary: dict) -> str:
    """Render Table 1 (run summary) as captioned markdown.

    Args:
        summary: The committed run summary.

    Returns:
        str: The markdown table.
    """
    rows = [
        ("Data root", f"`{summary['data_root']}`"),
        ("Data modality", summary["modality"]),
        ("Synthetic data", str(summary["synthetic"]).lower()),
        ("Provenance source", f"`{summary['provenance_source']}`"),
        ("Subjects", str(summary["n_subjects"])),
        ("Features", str(summary["n_features"])),
        ("Sites", str(summary["n_sites"])),
        ("Completed folds", str(summary["n_folds"])),
        ("Skipped sites", str(summary["n_sites_skipped"])),
        ("Nominal alpha", str(summary["alpha"])),
        ("Harmonization", summary["harmonization"]),
    ]
    body = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return (
        "**Table 1. LOSO benchmark run summary.** Values are copied from "
        "`reports/loso/loso_run_summary.json`, whose provenance is recorded "
        f"from `STAGING_REPORT.json`. {SCOPE_LABEL}\n\n"
        "| Quantity | Value |\n|---|---:|\n" + body + "\n"
    )


def render_table2(folds: pd.DataFrame) -> str:
    """Render Table 2 (per-fold metrics) as captioned markdown.

    Args:
        folds: The committed per-fold metrics.

    Returns:
        str: The markdown table.
    """
    lines = []
    for _, r in folds.iterrows():
        lines.append(
            f"| {r['held_out_site']} | {int(r['n_train'])} | {int(r['n_test'])} "
            f"| {_fmt(r['sign_consistency'])} | {_fmt(r['effect_map_correlation'])} "
            f"| {_fmt(r['heldout_significance'])} |"
        )
    body = "\n".join(lines)
    return (
        "**Table 2. Per-fold leave-one-site-out replication metrics.** Each "
        "row holds out one site, estimates case-control effects on the "
        "remaining sites, and scores replication on the unseen site. Source: "
        f"`reports/loso/loso_fold_metrics.csv`. {SCOPE_LABEL}\n\n"
        "| Held-out site | Train n | Test n | Sign consistency | "
        "Effect-map correlation | Held-out significance |\n"
        "|---|---:|---:|---:|---:|---:|\n" + body + "\n"
    )


def render_table3(summary: dict) -> str:
    """Render Table 3 (aggregate metrics) as captioned markdown.

    Args:
        summary: The committed run summary.

    Returns:
        str: The markdown table.
    """
    lines = []
    for metric, interpretation in INTERPRETATIONS.items():
        mean = summary[f"mean_{metric}"]
        n_defined = summary[f"n_folds_{metric}_defined"]
        n_folds = summary["n_folds"]
        lines.append(
            f"| {metric.replace('_', ' ').capitalize()} | {_fmt(mean)} "
            f"| {n_defined}/{n_folds} | {interpretation} |"
        )
    body = "\n".join(lines)
    return (
        "**Table 3. Aggregate LOSO benchmark results.** Means are over the "
        "folds for which each metric is defined; the values are deterministic "
        "for the committed synthetic seed and protected from silent drift by "
        f"`make check-repro`. {SCOPE_LABEL}\n\n"
        "| Metric | Mean | Defined folds | Interpretation |\n"
        "|---|---:|---:|---|\n" + body + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Render all Paper 1 tables from the committed artifacts.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        int: Exit code — 0 on success.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--loso-dir", type=Path, default=DEFAULT_LOSO_DIR)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args(argv)

    summary, folds = load_artifacts(args.loso_dir)
    tables = {
        "table1_run_summary.md": render_table1(summary),
        "table2_fold_metrics.md": render_table2(folds),
        "table3_aggregate_metrics.md": render_table3(summary),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in tables.items():
        (args.out_dir / name).write_text(text)
        print(f"wrote {args.out_dir / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
