"""Loaders for REST-meta-MDD Phase II features.

The real data are available only under the REST-meta-MDD Phase II Data
Use Agreement (DUA) via the R-fMRI Maps Project; they are NOT distributed
with this repository. Until access is approved (see docs/DATA_ACCESS.md),
all loaders raise :class:`DataAccessError` with actionable guidance.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

__all__ = ["DataAccessError", "load_features", "load_phenotypes", "load_dataset"]

_DUA_MESSAGE = (
    "REST-meta-MDD Phase II data require an approved Data Use Agreement.\n"
    "Apply via the R-fMRI Maps Project portal "
    "(http://rfmri.org/REST-meta-MDD) and follow the steps in "
    "docs/DATA_ACCESS.md. Real-data loaders are blocked until the DUA is "
    "approved and the downloaded files are placed under the configured "
    "data root."
)


class DataAccessError(RuntimeError):
    """Raised when REST-meta-MDD Phase II data are requested without an
    approved DUA / local data root."""


def _require_data_root(data_root: str | Path | None) -> Path:
    if data_root is None:
        raise DataAccessError(_DUA_MESSAGE)
    root = Path(data_root)
    if not root.exists():
        raise DataAccessError(
            f"Data root {root} does not exist. {_DUA_MESSAGE}"
        )
    return root


def load_features(
    data_root: str | Path | None = None,
    modality: str = "FC",
) -> pd.DataFrame:
    """Load a harmonization-ready feature matrix (subjects x features).

    Parameters
    ----------
    data_root:
        Local directory containing the REST-meta-MDD Phase II derivatives
        (only available after DUA approval).
    modality:
        One of ``"FC"``, ``"ALFF"``, ``"ReHo"``.
    """
    if modality not in {"FC", "ALFF", "ReHo"}:
        raise ValueError("modality must be one of 'FC', 'ALFF', 'ReHo'")
    root = _require_data_root(data_root)
    path = root / f"features_{modality.lower()}.csv"
    if not path.exists():
        raise DataAccessError(
            f"Expected feature file {path} not found. {_DUA_MESSAGE}"
        )
    return pd.read_csv(path, index_col=0)


def load_phenotypes(data_root: str | Path | None = None) -> pd.DataFrame:
    """Load subject phenotypes: ``subject``, ``site``, ``diagnosis`` (1=MDD, 0=HC)."""
    root = _require_data_root(data_root)
    path = root / "phenotypes.csv"
    if not path.exists():
        raise DataAccessError(
            f"Expected phenotype file {path} not found. {_DUA_MESSAGE}"
        )
    return pd.read_csv(path)


def load_dataset(
    data_root: str | Path | None = None,
    modality: str = "FC",
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Load (X, y, sites) aligned on subject ID for the LOSO benchmark."""
    feats = load_features(data_root, modality)
    phen = load_phenotypes(data_root)
    phen = phen.set_index("subject").loc[feats.index]
    X = feats
    y = phen["diagnosis"].to_numpy(dtype=int)
    sites = phen["site"].to_numpy()
    return X, y, sites
