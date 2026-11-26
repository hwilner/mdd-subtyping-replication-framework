"""Synthetic multi-site connectivity data with planted ground truth.

Generates a (subjects x features) matrix where:

- a subset of features carries a **replicable** case-control effect
  (same direction at every site),
- a subset carries a **non-replicable** effect (site-dependent, random
  direction — a stand-in for non-generalizing published findings),
- every site carries an additive + multiplicative **batch shift** so that
  ComBat harmonization can be validated.

Used by the test-suite to prove the ComBat + LOSO pipeline works before
real REST-meta-MDD Phase II data is available.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = ["SyntheticDataset", "simulate_multisite", "simulate_motion"]


@dataclass
class SyntheticDataset:
    """Synthetic dataset plus ground-truth bookkeeping."""

    X: pd.DataFrame
    y: np.ndarray
    sites: np.ndarray
    replicable_features: list[str]
    nonreplicable_features: list[str]
    null_features: list[str]
    batch_shifts: dict[str, dict[str, np.ndarray]]


def simulate_multisite(
    n_sites: int = 6,
    n_per_site: int = 40,
    case_fraction: float = 0.5,
    n_features: int = 60,
    n_replicable: int = 10,
    n_nonreplicable: int = 10,
    effect_size: float = 0.8,
    batch_shift_scale: float = 0.6,
    batch_scale_scale: float = 0.15,
    seed: int = 0,
) -> SyntheticDataset:
    """Simulate a multi-site case-control connectivity dataset.

    Args:
        n_sites:
            Number of sites (batches) to simulate.
        n_per_site:
            Subjects per site.
        case_fraction:
            Probability that a subject is a case (label 1).
        n_features:
            Total number of features in the matrix.
        n_replicable:
            Number of features carrying a replicable case-control effect
            (same direction at every site).
        n_nonreplicable:
            Number of features carrying a non-replicable effect (random sign
            per site).
        effect_size:
            Cohen's d of planted replicable effects (and magnitude of planted
            non-replicable effects before sign randomization).
        batch_shift_scale:
            SD of per-site additive batch offsets (units of feature SD).
        batch_scale_scale:
            SD of per-site multiplicative batch scaling around 1.0.
        seed:
            Seed for the random number generator; identical seeds reproduce
            identical datasets.

    Returns:
        SyntheticDataset: The simulated feature matrix, labels, site labels,
        and ground-truth bookkeeping.

    Raises:
        ValueError: If the planted effects exceed the number of features.
    """
    rng = np.random.default_rng(seed)
    if n_replicable + n_nonreplicable > n_features:
        raise ValueError("planted effects exceed number of features")

    n = n_sites * n_per_site
    sites = np.repeat(np.arange(n_sites), n_per_site)
    y = (rng.random(n) < case_fraction).astype(int)

    feature_names = [f"feat_{i:03d}" for i in range(n_features)]
    replicable = feature_names[:n_replicable]
    nonreplicable = feature_names[n_replicable : n_replicable + n_nonreplicable]
    null = feature_names[n_replicable + n_nonreplicable :]
    rep_idx = np.arange(n_replicable)
    nonrep_idx = np.arange(n_replicable, n_replicable + n_nonreplicable)

    X = rng.normal(0.0, 1.0, size=(n, n_features))

    # Planted replicable biological effect: same direction everywhere,
    # with heterogeneous magnitudes so the effect map has structure.
    rep_magnitudes = effect_size * np.linspace(0.5, 1.5, n_replicable)
    X[:, rep_idx] += (y[:, None] - 0.5) * 2 * rep_magnitudes

    # Planted non-replicable effect: random sign per site.
    for s in range(n_sites):
        mask = sites == s
        signs = rng.choice([-1.0, 1.0], size=len(nonrep_idx))
        X[np.ix_(mask, nonrep_idx)] += (y[mask, None] - 0.5) * 2 * effect_size * signs

    # Planted site batch shifts (additive + multiplicative, label-independent).
    batch_shifts: dict[str, dict[str, np.ndarray]] = {}
    for s in range(n_sites):
        loc = rng.normal(0.0, batch_shift_scale, size=n_features)
        scale = np.exp(rng.normal(0.0, batch_scale_scale, size=n_features))
        mask = sites == s
        X[mask] = X[mask] * scale + loc
        batch_shifts[f"site_{s}"] = {"loc": loc, "scale": scale}

    site_labels = np.array([f"site_{s}" for s in sites])
    return SyntheticDataset(
        X=pd.DataFrame(X, columns=feature_names),
        y=y,
        sites=site_labels,
        replicable_features=replicable,
        nonreplicable_features=nonreplicable,
        null_features=null,
        batch_shifts=batch_shifts,
    )


def simulate_motion(
    sites: np.ndarray,
    seed: int = 0,
    base_mean_mm: float = 0.10,
    site_shift_mm: float = 0.04,
    subject_noise_mm: float = 0.02,
    max_outliers_per_site: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate mean framewise displacement with planted motion outliers.

    Produces a deterministic ``mean_fd`` column (mm) for the synthetic demo
    so the issue-#13 QC machinery can be exercised end to end without DUA
    data. Baseline values are bounded in
    ``[base_mean_mm - site_shift_mm - subject_noise_mm,
      base_mean_mm + site_shift_mm + subject_noise_mm]``
    (default max 0.16 mm), so with the default 0.2 mm exclusion threshold
    every detected outlier is a planted one — the ground truth is exact by
    construction, for any seed.

    Args:
        sites: Site label per subject (used only for grouping; values may
            be strings or ints).
        seed: Seed for the random number generator; identical seeds
            reproduce identical columns.
        base_mean_mm: Cohort-average mean framewise displacement.
        site_shift_mm: Per-site scanner shift amplitude (uniform).
        subject_noise_mm: Within-site subject jitter amplitude (uniform).
        max_outliers_per_site: Site ``i`` (in sorted order) gets
            ``i % (max_outliers_per_site + 1)`` planted outliers, so the
            per-site outlier counts vary (0, 1, 2, 0, ...) and sites with
            zero planted outliers are also exercised.

    Returns:
        tuple[np.ndarray, np.ndarray]: The ``mean_fd`` values (mm) and a
        boolean mask marking the planted outliers (ground truth).
    """
    rng = np.random.default_rng(seed)
    sites = np.asarray(sites)
    unique = sorted(set(sites), key=str)
    n = len(sites)
    shift = {
        s: rng.uniform(-site_shift_mm, site_shift_mm) for s in unique
    }
    fd = np.array(
        [
            base_mean_mm + shift[s] + rng.uniform(-subject_noise_mm, subject_noise_mm)
            for s in sites
        ]
    )
    fd = np.clip(fd, 0.01, None)
    planted = np.zeros(n, dtype=bool)
    for i, s in enumerate(unique):
        n_out = i % (max_outliers_per_site + 1)
        if n_out == 0:
            continue
        idx = np.flatnonzero(sites == s)[:n_out]
        # Planted outliers sit clearly above any reasonable threshold.
        fd[idx] = 0.30 + 0.05 * rng.uniform(0.0, 1.0, size=n_out)
        planted[idx] = True
    return fd, planted
