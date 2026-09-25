"""Leave-one-site-out (LOSO) replication framework.

Given a multi-site feature matrix with case/control labels, the framework
holds out one site at a time, estimates effect sizes on the training
sites, and evaluates whether the effect replicates on the held-out site.

Metrics
-------
- ``sign_consistency``: fraction of training-derived significant effects
  whose held-out effect has the same sign.
- ``effect_map_correlation``: Pearson correlation between the training
  effect map (Cohen's d per feature) and the held-out effect map.
- ``heldout_significance``: fraction of training-significant effects that
  are also nominally significant (p < alpha) in the held-out site.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

__all__ = ["effect_sizes", "FoldResult", "LosoResult", "LosoReplicator"]


def effect_sizes(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cohen's d (case - control) and two-sample t-test p-values per feature."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    case = X[y == 1]
    ctrl = X[y == 0]
    if case.shape[0] < 2 or ctrl.shape[0] < 2:
        raise ValueError("Need at least 2 cases and 2 controls to compute effect sizes")
    n1, n0 = case.shape[0], ctrl.shape[0]
    m1, m0 = case.mean(axis=0), ctrl.mean(axis=0)
    v1, v0 = case.var(axis=0, ddof=1), ctrl.var(axis=0, ddof=1)
    pooled = np.sqrt(((n1 - 1) * v1 + (n0 - 1) * v0) / (n1 + n0 - 2))
    pooled = np.maximum(pooled, 1e-12)
    d = (m1 - m0) / pooled
    t, p = stats.ttest_ind(case, ctrl, axis=0, equal_var=False)
    return d, np.asarray(p)


@dataclass
class FoldResult:
    """Replication metrics for one held-out site."""

    held_out_site: str
    n_train: int
    n_test: int
    sign_consistency: float
    effect_map_correlation: float
    heldout_significance: float
    train_d: np.ndarray = field(repr=False)
    test_d: np.ndarray = field(repr=False)
    test_p: np.ndarray = field(repr=False)


@dataclass
class LosoResult:
    """Aggregate result over all LOSO folds."""

    folds: list[FoldResult]
    alpha: float

    def summary(self) -> pd.DataFrame:
        """Per-fold metrics as a DataFrame."""
        return pd.DataFrame(
            {
                "held_out_site": [f.held_out_site for f in self.folds],
                "n_train": [f.n_train for f in self.folds],
                "n_test": [f.n_test for f in self.folds],
                "sign_consistency": [f.sign_consistency for f in self.folds],
                "effect_map_correlation": [f.effect_map_correlation for f in self.folds],
                "heldout_significance": [f.heldout_significance for f in self.folds],
            }
        )

    @property
    def mean_sign_consistency(self) -> float:
        """Mean sign consistency.

        Returns:
            float: the sign consistency.
        """
        return float(np.mean([f.sign_consistency for f in self.folds]))

    @property
    def mean_effect_map_correlation(self) -> float:
        """Mean effect map correlation.

        Returns:
            float: the effect map correlation.
        """
        return float(np.mean([f.effect_map_correlation for f in self.folds]))

    @property
    def mean_heldout_significance(self) -> float:
        """Mean heldout significance.

        Returns:
            float: the heldout significance.
        """
        return float(np.mean([f.heldout_significance for f in self.folds]))


class LosoReplicator:
    """Leave-one-site-out replication of case-control effect maps.

    Parameters
    ----------
    alpha:
        Nominal p-value threshold for "significant" effects.
    min_train_sites:
        Minimum number of training sites required per fold.
    harmonize:
        Optional callable ``(X, sites) -> X_harmonized`` applied before
        splitting (e.g. :func:`loso_replication.combat.combat`).
    """

    def __init__(self, alpha: float = 0.05, min_train_sites: int = 2, harmonize=None):
        """Initialize the instance.

        Args:
            alpha (float): alpha.
            min_train_sites (int): min train sites.
            harmonize: harmonize.
        """
        self.alpha = alpha
        self.min_train_sites = min_train_sites
        self.harmonize = harmonize

    def split_sites(self, sites: np.ndarray) -> list[tuple[str, np.ndarray, np.ndarray]]:
        """Yield (held_out_site, train_idx, test_idx) for each site."""
        sites = np.asarray(sites)
        folds = []
        for s in np.unique(sites):
            test_idx = np.where(sites == s)[0]
            train_idx = np.where(sites != s)[0]
            folds.append((str(s), train_idx, test_idx))
        return folds

    def run(self, X: np.ndarray | pd.DataFrame, y: np.ndarray, sites: np.ndarray) -> LosoResult:
        """Run the full LOSO benchmark.

        Parameters
        ----------
        X:
            (n_samples, n_features) feature matrix.
        y:
            Binary labels, 1 = case (MDD), 0 = control.
        sites:
            Site label per sample.
        """
        X_arr = X.to_numpy(dtype=float) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
        y = np.asarray(y)
        sites = np.asarray(sites)
        if self.harmonize is not None:
            X_arr = np.asarray(self.harmonize(X_arr, sites), dtype=float)

        folds: list[FoldResult] = []
        for held, train_idx, test_idx in self.split_sites(sites):
            n_train_sites = len(np.unique(sites[train_idx]))
            if n_train_sites < self.min_train_sites:
                continue
            d_train, p_train = effect_sizes(X_arr[train_idx], y[train_idx])
            d_test, p_test = effect_sizes(X_arr[test_idx], y[test_idx])

            sig_train = p_train < self.alpha
            if sig_train.sum() == 0:
                sign_cons = np.nan
                held_sig = np.nan
            else:
                sign_cons = float(np.mean(np.sign(d_train[sig_train]) == np.sign(d_test[sig_train])))
                held_sig = float(np.mean(p_test[sig_train] < self.alpha))
            corr = float(np.corrcoef(d_train, d_test)[0, 1])

            folds.append(
                FoldResult(
                    held_out_site=held,
                    n_train=int(len(train_idx)),
                    n_test=int(len(test_idx)),
                    sign_consistency=sign_cons,
                    effect_map_correlation=corr,
                    heldout_significance=held_sig,
                    train_d=d_train,
                    test_d=d_test,
                    test_p=p_test,
                )
            )
        return LosoResult(folds=folds, alpha=self.alpha)
