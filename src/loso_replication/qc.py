"""Motion and preprocessing QC report machinery (issue #13).

Computes the input-QC report for the harmonization/benchmark inputs:

- motion outliers per site, from a framewise-displacement column in
  ``phenotypes.csv`` when one is present (column auto-detected from
  :data:`MOTION_COLUMN_CANDIDATES` or given explicitly);
- per-site exclusion counts (motion outliers union data-quality
  exclusions) and retained sample sizes;
- per-site feature-distribution summaries (pooled five-number summary,
  mean, SD) plus a deterministic SVG rendering.

Scope boundary (from the issue): this is QC of the *inputs* only. It never
touches the harmonization method, and pre/post-harmonization batch-effect
diagnostics live in :mod:`loso_replication.diagnostics`. When the staged
phenotypes carry no motion column (as with the minimal staged layout), the
motion block is reported as unavailable rather than estimated — QC numbers
are only ever computed from columns that actually exist in the input.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    "DEFAULT_MOTION_THRESHOLD_MM",
    "MOTION_COLUMN_CANDIDATES",
    "detect_motion_column",
    "motion_outlier_table",
    "exclusion_table",
    "feature_distribution_by_site",
    "render_feature_distribution_svg",
    "run_qc_report",
]

#: Default mean framewise-displacement exclusion threshold (mm). 0.2 mm is
#: the common resting-state exclusion threshold (Power et al. 2012); it is
#: a declared default, not a fitted parameter, and is recorded in every
#: report so the real-data run can pin a different pre-registered value.
DEFAULT_MOTION_THRESHOLD_MM = 0.2

#: Column names recognized as mean framewise displacement, in priority
#: order. The real REST-meta-MDD Phase II preprocessing logs use their own
#: naming; pass ``motion_column=`` explicitly if none of these match.
MOTION_COLUMN_CANDIDATES = (
    "mean_fd",
    "fd_mean",
    "mean_framewise_displacement",
    "framewise_displacement_mean",
)


def detect_motion_column(
    phen: pd.DataFrame, motion_column: str | None = None
) -> str | None:
    """Find the framewise-displacement column in a phenotypes table.

    Args:
        phen: The staged phenotypes table (one row per subject).
        motion_column: Explicit column name; wins over auto-detection.

    Returns:
        str | None: The column to use, or None if the table carries no
        recognizable motion column.

    Raises:
        ValueError: If an explicit ``motion_column`` is not present, or the
            selected column is not numeric. Silent fallback is never used:
            QC on the wrong column is worse than no motion QC.
    """
    if motion_column is not None:
        if motion_column not in phen.columns:
            raise ValueError(
                f"motion column {motion_column!r} not in phenotypes "
                f"columns {list(phen.columns)}"
            )
        column = motion_column
    else:
        column = next(
            (c for c in MOTION_COLUMN_CANDIDATES if c in phen.columns), None
        )
    if column is None:
        return None
    values = pd.to_numeric(phen[column], errors="coerce")
    if values.isna().any() and phen[column].notna().any():
        raise ValueError(f"motion column {column!r} is not numeric")
    return column


def motion_outlier_table(
    phen: pd.DataFrame,
    threshold_mm: float = DEFAULT_MOTION_THRESHOLD_MM,
    motion_column: str | None = None,
) -> dict:
    """Tabulate motion outliers per site.

    Args:
        phen: The staged phenotypes table with ``subject`` and ``site``.
        threshold_mm: Exclusion threshold on mean framewise displacement.
        motion_column: Explicit FD column; auto-detected when None.

    Returns:
        dict: ``available`` flag, the column/threshold used, and per-site
        outlier counts with the offending subject IDs listed (subject-level
        exclusion decisions must be auditable). When no motion column
        exists, ``available`` is False and no counts are invented.
    """
    column = detect_motion_column(phen, motion_column)
    if column is None:
        return {
            "available": False,
            "column": None,
            "threshold_mm": float(threshold_mm),
            "reason": "no motion column in phenotypes.csv (candidates: "
            + ", ".join(MOTION_COLUMN_CANDIDATES)
            + ")",
            "per_site": {},
            "total_outliers": None,
        }
    values = pd.to_numeric(phen[column], errors="coerce").to_numpy(dtype=float)
    outlier = values > threshold_mm
    per_site: dict[str, dict] = {}
    for site in sorted(phen["site"].unique(), key=str):
        mask = (phen["site"] == site).to_numpy()
        subjects = phen.loc[mask & outlier, "subject"].astype(str).tolist()
        per_site[str(site)] = {
            "n_subjects": int(mask.sum()),
            "n_motion_outliers": int(len(subjects)),
            "outlier_subjects": subjects,
            "max_fd_mm": float(np.nanmax(values[mask])) if mask.any() else None,
        }
    return {
        "available": True,
        "column": column,
        "threshold_mm": float(threshold_mm),
        "per_site": per_site,
        "total_outliers": int(outlier.sum()),
    }


def exclusion_table(
    phen: pd.DataFrame,
    X: pd.DataFrame,
    threshold_mm: float = DEFAULT_MOTION_THRESHOLD_MM,
    motion_column: str | None = None,
) -> dict:
    """Tabulate per-site exclusion and retained counts.

    A subject is excluded when it is a motion outlier (only when a motion
    column exists) or its feature row contains non-finite values. The two
    criteria are reported separately and as a union.

    Args:
        phen: The staged phenotypes table with ``subject`` and ``site``.
        X: The feature matrix, indexed by subject ID.
        threshold_mm: Motion exclusion threshold (ignored when no motion
            column exists).
        motion_column: Explicit FD column; auto-detected when None.

    Returns:
        dict: Per-site ``n_total`` / ``n_motion_excluded`` /
        ``n_data_excluded`` / ``n_excluded`` / ``n_retained`` plus totals.
    """
    column = detect_motion_column(phen, motion_column)
    phen = phen.set_index("subject")
    common = [s for s in X.index.astype(str) if s in phen.index.astype(str)]
    phen = phen.loc[common]
    finite = np.isfinite(X.loc[common].to_numpy(dtype=float)).all(axis=1)
    if column is not None:
        fd = pd.to_numeric(phen[column], errors="coerce").to_numpy(dtype=float)
        motion_excl = fd > threshold_mm
    else:
        motion_excl = np.zeros(len(common), dtype=bool)
    data_excl = ~finite
    excluded = motion_excl | data_excl
    sites = phen["site"].astype(str).to_numpy()
    per_site: dict[str, dict] = {}
    for site in sorted(set(sites)):
        mask = sites == site
        per_site[site] = {
            "n_total": int(mask.sum()),
            "n_motion_excluded": int((motion_excl & mask).sum()),
            "n_data_excluded": int((data_excl & mask).sum()),
            "n_excluded": int((excluded & mask).sum()),
            "n_retained": int((~excluded & mask).sum()),
        }
    return {
        "motion_criterion": (
            f"{column} > {threshold_mm} mm" if column is not None else None
        ),
        "data_criterion": "any non-finite feature value",
        "per_site": per_site,
        "n_total": int(len(common)),
        "n_excluded": int(excluded.sum()),
        "n_retained": int((~excluded).sum()),
    }


def feature_distribution_by_site(X: pd.DataFrame, sites: np.ndarray) -> dict:
    """Summarize the pooled feature-value distribution per site.

    Args:
        X: The feature matrix (subjects x features).
        sites: Site label per row of ``X``.

    Returns:
        dict: Per-site pooled five-number summary, mean, SD, and value
        count. Values are pooled over subjects and features; this is a
        distribution QC view (scanner scaling shifts show up here), not a
        per-feature statistical test.
    """
    sites = np.asarray(sites).astype(str)
    values = X.to_numpy(dtype=float)
    per_site: dict[str, dict] = {}
    for site in sorted(set(sites)):
        v = values[sites == site].ravel()
        q1, med, q3 = np.percentile(v, [25.0, 50.0, 75.0])
        per_site[site] = {
            "n_values": int(v.size),
            "mean": float(v.mean()),
            "sd": float(v.std(ddof=1)),
            "min": float(v.min()),
            "q1": float(q1),
            "median": float(med),
            "q3": float(q3),
            "max": float(v.max()),
        }
    return {"per_site": per_site}


def render_feature_distribution_svg(
    distributions: dict,
    modality: str,
    scope: str,
    threshold_note: str,
) -> str:
    """Render per-site pooled feature distributions as a boxplot-style SVG.

    The SVG is emitted directly (no plotting dependency) so the figure
    regenerates byte-identically in any environment, CI included — the same
    contract as ``reports/paper1/make_figures.py``.

    Args:
        distributions: The ``feature_distributions`` block from
            :func:`run_qc_report`.
        modality: Modality label for the title.
        scope: Scope label drawn on the canvas (synthetic demo vs. real).
        threshold_note: One-line note on the exclusion rule applied.

    Returns:
        str: The SVG document (deterministic byte content).
    """
    per_site = distributions["per_site"]
    sites = sorted(per_site)
    lo = min(s["min"] for s in per_site.values())
    hi = max(s["max"] for s in per_site.values())
    span = hi - lo or 1.0
    pad = 0.05 * span
    lo, hi = lo - pad, hi + pad
    span = hi - lo

    width, height = 820, 460
    left, right, top, bottom = 70, 24, 64, 84
    plot_w = width - left - right
    plot_h = height - top - bottom
    n = len(sites)
    slot = plot_w / n
    box_w = min(48.0, slot * 0.5)

    def y_pos(v: float) -> float:
        """Map a feature value to an SVG y coordinate."""
        return top + plot_h * (1.0 - (v - lo) / span)

    def fmt(v: float) -> str:
        """Format a coordinate/value deterministically."""
        return f"{v:.2f}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" font-family="sans-serif" font-size="12">',
        f'<text x="{width / 2:.0f}" y="24" text-anchor="middle" '
        f'font-size="15" font-weight="bold">Per-site feature distributions '
        f"({modality})</text>",
        f'<text x="{width / 2:.0f}" y="42" text-anchor="middle" '
        f'font-size="11" fill="#555">{scope}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" '
        f'y2="{top + plot_h}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" '
        f'stroke="#333"/>',
    ]
    # y-axis ticks
    for frac in np.linspace(0.0, 1.0, 6):
        v = lo + frac * span
        y = y_pos(v)
        parts.append(
            f'<line x1="{left - 4}" y1="{fmt(y)}" x2="{left}" y2="{fmt(y)}" '
            f'stroke="#333"/><text x="{left - 8}" y="{fmt(y + 4)}" '
            f'text-anchor="end" font-size="10">{v:.2f}</text>'
        )
    for i, site in enumerate(sites):
        s = per_site[site]
        cx = left + slot * (i + 0.5)
        y_min, y_q1 = y_pos(s["min"]), y_pos(s["q1"])
        y_med, y_q3 = y_pos(s["median"]), y_pos(s["q3"])
        y_max, y_mean = y_pos(s["max"]), y_pos(s["mean"])
        parts += [
            f'<line x1="{fmt(cx)}" y1="{fmt(y_min)}" x2="{fmt(cx)}" '
            f'y2="{fmt(y_max)}" stroke="#4c78a8" stroke-width="1.5"/>',
            f'<rect x="{fmt(cx - box_w / 2)}" y="{fmt(y_q3)}" '
            f'width="{fmt(box_w)}" height="{fmt(max(y_q1 - y_q3, 0.5))}" '
            f'fill="#4c78a8" fill-opacity="0.35" stroke="#4c78a8"/>',
            f'<line x1="{fmt(cx - box_w / 2)}" y1="{fmt(y_med)}" '
            f'x2="{fmt(cx + box_w / 2)}" y2="{fmt(y_med)}" stroke="#1f3a5f" '
            f'stroke-width="2"/>',
            f'<circle cx="{fmt(cx)}" cy="{fmt(y_mean)}" r="3" '
            f'fill="#f58518"/>',
            f'<text x="{fmt(cx)}" y="{top + plot_h + 16}" '
            f'text-anchor="middle" font-size="11">site {site}</text>',
            f'<text x="{fmt(cx)}" y="{top + plot_h + 30}" '
            f'text-anchor="middle" font-size="9" fill="#555">'
            f'n={s["n_values"]}</text>',
        ]
    parts += [
        f'<text x="{left}" y="{height - 20}" font-size="10" fill="#555">'
        f"Box = pooled feature-value IQR per site; whiskers = min/max; "
        f'orange dot = mean. {threshold_note}</text>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def run_qc_report(
    X: pd.DataFrame,
    phen: pd.DataFrame,
    threshold_mm: float = DEFAULT_MOTION_THRESHOLD_MM,
    motion_column: str | None = None,
) -> dict:
    """Compute the full input-QC report.

    Args:
        X: The feature matrix, indexed by subject ID.
        phen: The staged phenotypes table with ``subject`` and ``site``.
        threshold_mm: Motion exclusion threshold.
        motion_column: Explicit FD column; auto-detected when None.

    Returns:
        dict: JSON-serializable report with ``motion``, ``exclusions``, and
        ``feature_distributions`` blocks. Contains only quantities computed
        from the inputs; absent motion data is reported as unavailable,
        never estimated.
    """
    phen = phen.copy()
    phen["subject"] = phen["subject"].astype(str)
    X = X.copy()
    X.index = X.index.astype(str)
    aligned = phen.set_index("subject").loc[X.index]
    sites = aligned["site"].astype(str).to_numpy()
    return {
        "motion": motion_outlier_table(phen, threshold_mm, motion_column),
        "exclusions": exclusion_table(phen, X, threshold_mm, motion_column),
        "feature_distributions": feature_distribution_by_site(X, sites),
    }
