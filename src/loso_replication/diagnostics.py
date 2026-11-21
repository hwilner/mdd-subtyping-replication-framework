"""Pre/post-harmonization batch-effect diagnostics (issue #10).

Computes diagnostics that quantify how much site-related variance a
feature matrix carries before and after ComBat harmonization, and whether
the biological (case-control) signal survives the correction:

- :func:`site_variance_decomposition` — per-feature eta^2 of site
  (fraction of each feature's variance explained by site membership).
- :func:`site_classification_accuracy` — cross-validated accuracy of a
  multinomial logistic regression predicting site from the features; a
  successful harmonization drives this toward chance.
- :func:`cohens_d_map` / :func:`biological_preservation` — per-feature
  case-control Cohen's d before vs. after harmonization; the effect map
  should be preserved if ComBat removed only batch signal.
- :func:`run_batch_diagnostics` — the full pre/post report as a
  JSON-serializable dict.

Diagnostics only: the harmonization method itself is never modified here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .combat import combat

__all__ = [
    "site_variance_decomposition",
    "site_classification_accuracy",
    "cohens_d_map",
    "biological_preservation",
    "site_mean_spread",
    "run_batch_diagnostics",
]


def _as_arrays(
    data: np.ndarray | pd.DataFrame, sites: np.ndarray | pd.Series
) -> tuple[np.ndarray, np.ndarray]:
    """Coerce inputs to ``(n_samples, n_features)`` and ``(n_samples,)`` arrays."""
    arr = data.to_numpy(dtype=float) if isinstance(data, pd.DataFrame) else np.asarray(data, dtype=float)
    site_arr = sites.to_numpy() if isinstance(sites, pd.Series) else np.asarray(sites)
    if arr.ndim != 2:
        raise ValueError("data must be a 2D (n_samples, n_features) matrix")
    if arr.shape[0] != site_arr.shape[0]:
        raise ValueError("sites length must match number of rows of data")
    if np.unique(site_arr).size < 2:
        raise ValueError("at least two sites are required for batch diagnostics")
    return arr, site_arr


def site_variance_decomposition(
    data: np.ndarray | pd.DataFrame, sites: np.ndarray | pd.Series
) -> pd.DataFrame:
    """Per-feature fraction of variance explained by site (one-way ANOVA eta^2).

    Args:
        data: (n_samples, n_features) feature matrix.
        sites: Length-n_samples site label per row.

    Returns:
        pd.DataFrame: One row per feature with columns ``feature``,
        ``ss_between``, ``ss_total``, and ``eta_squared`` in [0, 1].
    """
    arr, site_arr = _as_arrays(data, sites)
    columns = list(data.columns) if isinstance(data, pd.DataFrame) else [f"f{i}" for i in range(arr.shape[1])]
    grand_mean = arr.mean(axis=0)
    ss_total = ((arr - grand_mean) ** 2).sum(axis=0)
    ss_between = np.zeros(arr.shape[1])
    for level in np.unique(site_arr):
        mask = site_arr == level
        diff = arr[mask].mean(axis=0) - grand_mean
        ss_between += mask.sum() * diff**2
    eta2 = np.divide(ss_between, ss_total, out=np.zeros_like(ss_between), where=ss_total > 0)
    return pd.DataFrame(
        {"feature": columns, "ss_between": ss_between, "ss_total": ss_total, "eta_squared": eta2}
    )


def site_classification_accuracy(
    data: np.ndarray | pd.DataFrame,
    sites: np.ndarray | pd.Series,
    *,
    n_splits: int = 5,
    seed: int = 0,
) -> dict:
    """Cross-validated accuracy of predicting site from the feature matrix.

    A multinomial logistic regression on standardized features is scored
    with stratified K-fold cross-validation. High accuracy means site
    identity is readable from the features (batch signal); accuracy near
    the majority-class chance level means it is not.

    Args:
        data: (n_samples, n_features) feature matrix.
        sites: Length-n_samples site label per row.
        n_splits: Number of stratified cross-validation folds.
        seed: Random state for the fold shuffling (deterministic).

    Returns:
        dict: ``accuracy`` (mean CV accuracy), ``per_fold`` accuracies,
        ``chance_majority`` (largest site fraction), ``n_sites``, and the
        classifier recipe for the report.
    """
    arr, site_arr = _as_arrays(data, sites)
    counts = pd.Series(site_arr).value_counts()
    n_splits = int(min(n_splits, counts.min()))
    if n_splits < 2:
        raise ValueError("smallest site has fewer than 2 subjects; cannot cross-validate")
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    scores = cross_val_score(clf, arr, site_arr, cv=cv)
    return {
        "accuracy": float(scores.mean()),
        "per_fold": [float(s) for s in scores],
        "chance_majority": float(counts.iloc[0] / counts.sum()),
        "n_sites": int(counts.size),
        "model": "StandardScaler + multinomial LogisticRegression(max_iter=1000)",
        "cv": f"StratifiedKFold(n_splits={n_splits}, shuffle=True, random_state={seed})",
    }


def cohens_d_map(data: np.ndarray | pd.DataFrame, y: np.ndarray) -> np.ndarray:
    """Per-feature Cohen's d of the case-control contrast (case minus control).

    Args:
        data: (n_samples, n_features) feature matrix.
        y: Length-n_samples binary diagnosis (1 = case, 0 = control).

    Returns:
        np.ndarray: Cohen's d per feature; 0.0 where the pooled SD is ~0.

    Raises:
        ValueError: If either class has fewer than 2 subjects.
    """
    arr = data.to_numpy(dtype=float) if isinstance(data, pd.DataFrame) else np.asarray(data, dtype=float)
    y = np.asarray(y)
    if arr.shape[0] != y.shape[0]:
        raise ValueError("y length must match number of rows of data")
    case, ctrl = arr[y == 1], arr[y == 0]
    if case.shape[0] < 2 or ctrl.shape[0] < 2:
        raise ValueError("need at least 2 cases and 2 controls for Cohen's d")
    n1, n0 = case.shape[0], ctrl.shape[0]
    pooled = np.sqrt(
        ((n1 - 1) * case.var(axis=0, ddof=1) + (n0 - 1) * ctrl.var(axis=0, ddof=1))
        / (n1 + n0 - 2)
    )
    return np.divide(case.mean(axis=0) - ctrl.mean(axis=0), pooled, out=np.zeros_like(pooled), where=pooled > 1e-12)


def biological_preservation(
    data_pre: np.ndarray | pd.DataFrame,
    data_post: np.ndarray | pd.DataFrame,
    y: np.ndarray,
) -> dict:
    """Whether the case-control effect map survives harmonization.

    Args:
        data_pre: Feature matrix before harmonization.
        data_post: Feature matrix after harmonization (same rows/columns).
        y: Length-n_samples binary diagnosis.

    Returns:
        dict: Pearson correlation between the pre and post Cohen's d maps,
        mean |d| before and after, and per-feature counts where the sign
        of d flipped.
    """
    d_pre = cohens_d_map(data_pre, y)
    d_post = cohens_d_map(data_post, y)
    corr = float(np.corrcoef(d_pre, d_post)[0, 1])
    return {
        "effect_map_correlation": corr,
        "mean_abs_d_pre": float(np.abs(d_pre).mean()),
        "mean_abs_d_post": float(np.abs(d_post).mean()),
        "sign_flips": int((np.sign(d_pre) != np.sign(d_post)).sum()),
        "n_features": int(d_pre.size),
    }


def site_mean_spread(data: np.ndarray | pd.DataFrame, sites: np.ndarray | pd.Series) -> dict:
    """Between-site spread of per-site feature means (distribution shift).

    Args:
        data: (n_samples, n_features) feature matrix.
        sites: Length-n_samples site label per row.

    Returns:
        dict: Mean, median, and max over features of the standard
        deviation of per-site means — a compact per-site distribution
        shift summary.
    """
    arr, site_arr = _as_arrays(data, sites)
    site_means = np.vstack([arr[site_arr == level].mean(axis=0) for level in np.unique(site_arr)])
    spread = site_means.std(axis=0, ddof=1)
    return {
        "mean": float(spread.mean()),
        "median": float(np.median(spread)),
        "max": float(spread.max()),
    }


def run_batch_diagnostics(
    data: np.ndarray | pd.DataFrame,
    y: np.ndarray,
    sites: np.ndarray | pd.Series,
    *,
    seed: int = 0,
    n_splits: int = 5,
) -> dict:
    """Full pre/post-ComBat batch-effect diagnostics report.

    Harmonizes ``data`` with the built-in empirical-Bayes ComBat (the
    same backend the demo benchmark records) and compares site signal
    and biological signal before vs. after.

    Args:
        data: (n_samples, n_features) feature matrix.
        y: Length-n_samples binary diagnosis.
        sites: Length-n_samples site label per row.
        seed: Random state for the site-classification folds.
        n_splits: Number of cross-validation folds for site
            classification.

    Returns:
        dict: JSON-serializable report with ``pre``/``post`` blocks for
        site eta^2, site classification, and site-mean spread, plus a
        ``biological_preservation`` block. No data are modified.
    """
    arr, site_arr = _as_arrays(data, sites)
    frame = data if isinstance(data, pd.DataFrame) else pd.DataFrame(arr)
    harmonized = combat(frame, site_arr, prefer_neurocombat=False)

    def _site_block(mat: pd.DataFrame) -> dict:
        eta = site_variance_decomposition(mat, site_arr)["eta_squared"]
        return {
            "eta_squared_mean": float(eta.mean()),
            "eta_squared_median": float(eta.median()),
            "eta_squared_max": float(eta.max()),
            "site_classification": site_classification_accuracy(mat, site_arr, n_splits=n_splits, seed=seed),
            "site_mean_spread": site_mean_spread(mat, site_arr),
        }

    return {
        "harmonization": "combat (built-in empirical Bayes)",
        "n_subjects": int(arr.shape[0]),
        "n_features": int(arr.shape[1]),
        "n_sites": int(np.unique(site_arr).size),
        "pre": _site_block(frame),
        "post": _site_block(harmonized),
        "biological_preservation": biological_preservation(frame, harmonized, np.asarray(y)),
    }
