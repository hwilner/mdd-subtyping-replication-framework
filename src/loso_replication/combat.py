"""ComBat harmonization (empirical Bayes) for feature matrices with site labels.

The public entry point is :func:`combat`. If the optional ``neuroCombat``
package is installed it is used; otherwise a self-contained implementation
of the empirical-Bayes ComBat algorithm (Johnson, Li & Rabinovic, 2007)
is used. Both paths share the same API.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["combat", "CombatHarmonizer", "HAS_NEUROCOMBAT"]

try:  # optional third-party implementation
    from neuroCombat import neuroCombat as _neuro_combat

    HAS_NEUROCOMBAT = True
except Exception:  # pragma: no cover - exercised implicitly on CI
    _neuro_combat = None
    HAS_NEUROCOMBAT = False


def _design_matrix(site_codes: np.ndarray, n_batches: int) -> np.ndarray:
    """Intercept + site indicator columns (drop-first to avoid collinearity)."""
    n = site_codes.shape[0]
    design = np.zeros((n, n_batches))
    design[:, 0] = 1.0
    for b in range(1, n_batches):
        design[:, b] = (site_codes == b).astype(float)
    return design


def _builtin_combat(
    data: np.ndarray,
    sites: np.ndarray,
    *,
    ref_batch: str | None = None,
) -> np.ndarray:
    """Self-contained empirical-Bayes ComBat for a (n_samples, n_features) matrix.

    Removes additive and multiplicative site effects while preserving the
    grand mean per feature. ``data`` is assumed already aligned column-wise.
    """
    data = np.asarray(data, dtype=float)
    sites = np.asarray(sites)
    if data.ndim != 2:
        raise ValueError("data must be a 2D (n_samples, n_features) matrix")
    if data.shape[0] != sites.shape[0]:
        raise ValueError("sites length must match number of rows of data")

    batch_levels, site_codes = np.unique(sites, return_inverse=True)
    n_batches = len(batch_levels)
    if n_batches < 2:
        return data.copy()
    if ref_batch is not None:
        if ref_batch not in set(batch_levels):
            raise ValueError(f"ref_batch {ref_batch!r} not present in sites")

    n_samples, n_features = data.shape
    design = _design_matrix(site_codes, n_batches)

    # Standardize data to the grand mean / pooled variance.
    B_hat = np.linalg.pinv(design.T @ design) @ design.T @ data
    grand_mean = B_hat[0]  # (n_features,)
    var_pooled = ((data - design @ B_hat) ** 2).sum(axis=0) / n_samples
    var_pooled = np.maximum(var_pooled, 1e-12)
    stand_data = (data - grand_mean) / np.sqrt(var_pooled)

    # Per-batch additive (gamma) and multiplicative (delta) estimates.
    gamma_hat = np.zeros((n_batches, n_features))
    delta_hat = np.zeros((n_batches, n_features))
    for b in range(n_batches):
        mask = site_codes == b
        batch_data = stand_data[mask]
        gamma_hat[b] = batch_data.mean(axis=0)
        delta_hat[b] = np.maximum(batch_data.var(axis=0, ddof=1), 1e-12)

    # Empirical-Bayes hyperparameters.
    gamma_bar = gamma_hat.mean(axis=0)
    t2 = np.maximum(gamma_hat.var(axis=0, ddof=1), 1e-12)
    # Method-of-moments priors for inverse-gamma on delta.
    delta_mean = delta_hat.mean(axis=0)
    delta_var = np.maximum(delta_hat.var(axis=0, ddof=1), 1e-12)
    a_prior = delta_mean**2 / delta_var + 2.0
    b_prior = delta_mean * (delta_mean**2 / delta_var + 1.0)

    # Empirical-Bayes posterior estimates.
    n_per_batch = np.array([(site_codes == b).sum() for b in range(n_batches)], dtype=float)
    gamma_star = (n_per_batch[:, None] * t2[None, :] * gamma_hat
                  + var_pooled[None, :] * gamma_bar[None, :]) / (
        n_per_batch[:, None] * t2[None, :] + var_pooled[None, :]
    )
    delta_star = np.zeros_like(delta_hat)
    for b in range(n_batches):
        n_b = n_per_batch[b]
        theta = (b_prior + 0.5 * n_b * delta_hat[b]) / (a_prior + 0.5 * n_b - 1.0 + 1e-12)
        delta_star[b] = np.maximum(theta, 1e-8)

    # Adjust.
    adjusted = stand_data.copy()
    for b in range(n_batches):
        mask = site_codes == b
        adjusted[mask] = (stand_data[mask] - gamma_star[b]) / np.sqrt(delta_star[b])
    adjusted = adjusted * np.sqrt(var_pooled) + grand_mean
    return adjusted


def combat(
    data: np.ndarray | pd.DataFrame,
    sites: np.ndarray | pd.Series,
    *,
    ref_batch: str | None = None,
    prefer_neurocombat: bool = True,
) -> np.ndarray | pd.DataFrame:
    """Harmonize a feature matrix across sites with ComBat.

    Parameters
    ----------
    data:
    (n_samples, n_features) matrix of connectivity/ALFF/ReHo features.
    sites:
    Length-n_samples site label per row.
    ref_batch:
    Optional site to treat as the reference batch.
    prefer_neurocombat:
    Use the optional ``neuroCombat`` package when available; otherwise
    fall back to the built-in empirical-Bayes implementation.

    Returns:
    -------
    Harmonized matrix, same type/shape as ``data``.
    """
    is_df = isinstance(data, pd.DataFrame)
    arr = data.to_numpy(dtype=float) if is_df else np.asarray(data, dtype=float)
    site_arr = sites.to_numpy() if isinstance(sites, pd.Series) else np.asarray(sites)

    if prefer_neurocombat and HAS_NEUROCOMBAT and ref_batch is None:
        df = pd.DataFrame(arr, columns=[f"f{i}" for i in range(arr.shape[1])])
        covars = pd.DataFrame({"site": site_arr.astype(str)})
        out = _neuro_combat(dat=df.T, covars=covars, batch_col="site")["data"].T.to_numpy()
    else:
        out = _builtin_combat(arr, site_arr, ref_batch=ref_batch)

    if is_df:
        return pd.DataFrame(out, index=data.index, columns=data.columns)
    return out


class CombatHarmonizer:
    """Small sklearn-style wrapper around :func:`combat`."""

    def __init__(self, prefer_neurocombat: bool = True):
        """Initialize the instance.

        Args:
        prefer_neurocombat (bool): prefer neurocombat.
        """
        self.prefer_neurocombat = prefer_neurocombat

    def fit_transform(self, data, sites):
        """Fit transform.

        Args:
        data: data.
        sites: sites.

        Returns:
        The transform.
        """
        return combat(data, sites, prefer_neurocombat=self.prefer_neurocombat)

    # ComBat requires batch labels for new data; kept for API symmetry.
    def transform(self, data, sites):  # noqa: D102
        return self.fit_transform(data, sites)
