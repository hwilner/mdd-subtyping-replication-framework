#!/usr/bin/env python
"""Render Paper 1 figures from committed artifacts (issue #7).

Reads only committed results artifacts and writes SVG figures — no
benchmark quantity is recomputed, and no plotting dependency is required
(the SVG is emitted directly so the figure regenerates byte-identically in
any environment, CI included).

Currently rendered:

- Figure 2 (synthetic demo): the three LOSO replication metrics for each
  held-out site, from ``reports/loso/loso_fold_metrics.csv``. The real-data
  version of this figure is authorized by issue #14 after fold execution
  (issue #9); this demo rendering exists to lock the plotting contract.

Usage:

    python reports/paper1/make_figures.py            # writes reports/paper1/
    python reports/paper1/make_figures.py --out-dir /tmp/out
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOSO_DIR = REPO_ROOT / "reports" / "loso"
DEFAULT_OUT_DIR = REPO_ROOT / "reports" / "paper1"

METRICS = (
    ("sign_consistency", "Sign consistency", "#4c78a8"),
    ("effect_map_correlation", "Effect-map correlation", "#f58518"),
    ("heldout_significance", "Held-out significance", "#54a24b"),
)

CAPTION = (
    "Figure 2 (synthetic demo). Leave-one-site-out replication metrics by "
    "held-out site: sign consistency, effect-map correlation, and held-out "
    "significance for the six synthetic demo sites. Source: "
    "reports/loso/loso_fold_metrics.csv (deterministic synthetic benchmark; "
    "not an MDD finding). The real-data version of this figure is planned "
    "under issue #14 after real fold execution (issue #9)."
)


def render_figure2(folds: pd.DataFrame) -> str:
    """Render the per-site metric distribution as a grouped-bar SVG.

    Args:
        folds: The committed per-fold metrics.

    Returns:
        str: The SVG document (deterministic byte content).

    Raises:
        ValueError: If a metric value falls outside [0, 1] — these are
            fractions/correlations of a replication benchmark, and an
            out-of-range value means the artifact is corrupt.
    """
    width, height = 780, 440
    left, right, top, bottom = 64, 20, 56, 76
    plot_w = width - left - right
    plot_h = height - top - bottom
    sites = [str(s) for s in folds["held_out_site"]]
    n_groups = len(sites)
    n_bars = len(METRICS)
    group_w = plot_w / n_groups
    bar_w = group_w / (n_bars + 1)

    def y_pos(v: float) -> float:
        """Map a metric value in [0, 1] to an SVG y coordinate.

        Args:
            v: The metric value.

        Returns:
            float: The y pixel coordinate.
        """
        return top + plot_h * (1.0 - v)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        'font-family="Helvetica, Arial, sans-serif">',
        f"<title>Figure 2 (synthetic demo): LOSO replication metrics by "
        f"held-out site</title>",
        f"<desc>{CAPTION}</desc>",
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]
    # Gridlines and y-axis labels at 0.0, 0.2, ..., 1.0.
    for i in range(6):
        v = i / 5.0
        y = y_pos(v)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" '
            f'stroke="{"#888888" if i == 0 else "#dddddd"}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-size="11" fill="#444444">{v:.1f}</text>'
        )
    # Bars.
    for gi, (_, row) in enumerate(folds.iterrows()):
        gx = left + gi * group_w
        for bi, (col, _label, color) in enumerate(METRICS):
            v = float(row[col])
            if not (0.0 <= v <= 1.0):
                raise ValueError(
                    f"{col}={v} for {row['held_out_site']} is outside [0, 1]; "
                    "the committed artifact looks corrupt."
                )
            x = gx + bar_w * (0.5 + bi)
            parts.append(
                f'<rect x="{x:.2f}" y="{y_pos(v):.2f}" width="{bar_w:.2f}" '
                f'height="{plot_h - (y_pos(v) - top):.2f}" fill="{color}"/>'
            )
        parts.append(
            f'<text x="{gx + group_w / 2:.2f}" y="{height - bottom + 18}" '
            f'text-anchor="middle" font-size="12" fill="#222222">'
            f'{row["held_out_site"]}</text>'
        )
    # Axis titles.
    parts.append(
        f'<text x="{left + plot_w / 2:.2f}" y="{height - 14}" '
        f'text-anchor="middle" font-size="13" fill="#222222">'
        f'Held-out site</text>'
    )
    parts.append(
        f'<text x="16" y="{top + plot_h / 2:.2f}" text-anchor="middle" '
        f'font-size="13" fill="#222222" transform="rotate(-90 16 '
        f'{top + plot_h / 2:.2f})">Metric value</text>'
    )
    parts.append(
        f'<text x="{left + plot_w / 2:.2f}" y="24" text-anchor="middle" '
        f'font-size="14" font-weight="bold" fill="#111111">Figure 2 '
        f'(synthetic demo): LOSO replication metrics by held-out site</text>'
    )
    # Legend, top right, one row per metric.
    lx = width - right - 190
    ly = top - 16
    for bi, (_col, label, color) in enumerate(METRICS):
        y = ly + bi * 18
        parts.append(
            f'<rect x="{lx}" y="{y - 10}" width="12" height="12" '
            f'fill="{color}"/>'
        )
        parts.append(
            f'<text x="{lx + 18}" y="{y}" font-size="11" '
            f'fill="#222222">{label}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Render all Paper 1 figures from the committed artifacts.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        int: Exit code — 0 on success.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--loso-dir", type=Path, default=DEFAULT_LOSO_DIR)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args(argv)

    folds = pd.read_csv(args.loso_dir / "loso_fold_metrics.csv")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / "fig2_loso_metrics_by_site_demo.svg"
    out.write_text(render_figure2(folds))
    (args.out_dir / "fig2_caption.md").write_text(f"**{CAPTION}**\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
