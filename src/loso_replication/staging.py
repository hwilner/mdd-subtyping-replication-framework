"""Post-DUA staging for REST-meta-MDD Phase II derivatives.

The real data are available only under the REST-meta-MDD Phase II Data
Use Agreement (DUA) via the R-fMRI Maps Project and must never be
committed. Once the DUA is approved and the files are downloaded, this
module:

1. checks the expected file layout (``phenotypes.csv`` +
   ``features_{fc,alff,reho}.csv``),
2. runs integrity checks (row alignment on subject ID, binary diagnosis,
   numeric feature matrix, no all-NaN columns, >= 2 sites),
3. converts the staged files into the framework's data structures
   (the ``(X, y, sites)`` triple consumed by
   :class:`loso_replication.loso.LosoReplicator`), and
4. writes a ``STAGING_REPORT.json`` summarizing the staged dataset.

A ``--synthetic`` demo mode (see :func:`stage_synthetic_demo`) writes a
small synthetic dataset in exactly the staged layout so the full
prepare -> benchmark path can be exercised without the DUA data.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .io import DataAccessError, load_dataset
from .simulate import simulate_multisite

__all__ = [
    "EXPECTED_LAYOUT",
    "StagingError",
    "stage_synthetic_demo",
    "validate_staged",
    "load_staged_dataset",
]

#: Files the staging step expects in the data root (see docs/DATA_ACCESS.md).
EXPECTED_LAYOUT = {
    "phenotypes.csv": "columns: subject, site, diagnosis (1=MDD, 0=HC)",
    "features_fc.csv": "subjects x features matrix, subject IDs as index",
    "features_alff.csv": "subjects x features matrix, subject IDs as index",
    "features_reho.csv": "subjects x features matrix, subject IDs as index",
}

_MODALITY_FILES = {"FC": "features_fc.csv", "ALFF": "features_alff.csv",
                   "ReHo": "features_reho.csv"}


class StagingError(RuntimeError):
    """Raised when staged REST-meta-MDD files fail integrity checks."""


def validate_staged(data_root: str | Path, modalities: tuple[str, ...] = ("FC",)) -> dict:
    """Validate the staged file layout and contents.

    Returns a report dict (also suitable for ``STAGING_REPORT.json``).
    Raises :class:`StagingError` with an actionable message on failure.
    """
    root = Path(data_root)
    if not root.exists():
        raise StagingError(f"Data root {root} does not exist")

    phen_path = root / "phenotypes.csv"
    if not phen_path.exists():
        raise StagingError(
            f"Missing {phen_path}. Expected layout: {EXPECTED_LAYOUT}"
        )
    phen = pd.read_csv(phen_path)
    required = {"subject", "site", "diagnosis"}
    if not required <= set(phen.columns):
        raise StagingError(
            f"{phen_path} must have columns {sorted(required)}; "
            f"got {list(phen.columns)}"
        )
    if not set(np.unique(phen["diagnosis"])) <= {0, 1}:
        raise StagingError("diagnosis must be binary (1=MDD, 0=HC)")
    if phen["subject"].duplicated().any():
        raise StagingError("duplicate subject IDs in phenotypes.csv")
    n_sites = phen["site"].nunique()
    if n_sites < 2:
        raise StagingError("LOSO requires subjects from at least 2 sites")

    report = {
        "data_root": str(root),
        "n_subjects": int(len(phen)),
        "n_sites": int(n_sites),
        "n_cases": int((phen["diagnosis"] == 1).sum()),
        "n_controls": int((phen["diagnosis"] == 0).sum()),
        "modalities": {},
    }
    for modality in modalities:
        fname = _MODALITY_FILES[modality]
        fpath = root / fname
        if not fpath.exists():
            raise StagingError(
                f"Missing {fpath}. Expected layout: {EXPECTED_LAYOUT}"
            )
        feats = pd.read_csv(fpath, index_col=0)
        if feats.empty or feats.shape[1] == 0:
            raise StagingError(f"{fname} is empty")
        if not np.isfinite(feats.to_numpy(dtype=float)).all():
            raise StagingError(f"{fname} contains NaN/inf values")
        missing = set(feats.index.astype(str)) - set(phen["subject"].astype(str))
        if missing:
            raise StagingError(
                f"{fname}: {len(missing)} subject IDs have no phenotype row "
                f"(e.g. {sorted(missing)[:3]})"
            )
        report["modalities"][modality] = {
            "file": fname,
            "n_subjects": int(feats.shape[0]),
            "n_features": int(feats.shape[1]),
        }
    return report


def load_staged_dataset(
    data_root: str | Path, modality: str = "FC"
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Validate, then load the staged dataset as ``(X, y, sites)``."""
    validate_staged(data_root, modalities=(modality,))
    return load_dataset(data_root, modality)


def stage_synthetic_demo(
    data_root: str | Path,
    n_sites: int = 6,
    n_per_site: int = 40,
    n_features: int = 60,
    seed: int = 0,
) -> dict:
    """Write a synthetic dataset in the exact staged layout (demo mode).

    Used to exercise the prepare -> benchmark path without DUA data. The
    synthetic data carry planted replicable effects, planted site batch
    shifts, and known ground truth (see :mod:`loso_replication.simulate`).
    """
    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)
    ds = simulate_multisite(
        n_sites=n_sites, n_per_site=n_per_site, n_features=n_features, seed=seed
    )
    X = ds.X.copy()
    X.index = [f"sub{i:04d}" for i in range(len(X))]
    X.to_csv(root / "features_fc.csv")
    pd.DataFrame(
        {"subject": X.index, "site": ds.sites, "diagnosis": ds.y}
    ).to_csv(root / "phenotypes.csv", index=False)

    report = validate_staged(root, modalities=("FC",))
    report["synthetic"] = True
    report["seed"] = seed
    report["replicable_features"] = ds.replicable_features
    (root / "STAGING_REPORT.json").write_text(json.dumps(report, indent=2))
    return report


def write_staging_report(data_root: str | Path, report: dict) -> Path:
    path = Path(data_root) / "STAGING_REPORT.json"
    path.write_text(json.dumps(report, indent=2))
    return path
