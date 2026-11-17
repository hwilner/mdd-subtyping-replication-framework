"""Fold configuration for the LOSO benchmark (issue #6).

A fold configuration enumerates one leave-one-site-out fold per site in a
dataset, recording the fold's size and whether it is runnable before any
computation happens. The configuration is serializable to JSON so that a
job array (issue #9) can enumerate folds without loading the dataset, and
so that skipped folds are recorded with an explicit reason rather than
silently dropped.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

__all__ = ["FOLD_CONFIG_SCHEMA", "FoldSpec", "build_fold_config",
           "read_fold_config", "write_fold_config"]

#: Schema tag written into every fold-config JSON, so future readers can
#: detect format changes instead of misparsing them.
FOLD_CONFIG_SCHEMA = "loso-fold-config/v1"


@dataclass
class FoldSpec:
    """One leave-one-site-out fold.

    Attributes:
        held_out_site: The site held out for evaluation in this fold.
        n_train: Number of training subjects (all other sites).
        n_test: Number of subjects at the held-out site.
        n_train_sites: Number of distinct training sites.
        n_cases_test: Cases at the held-out site (None if labels were not
            provided to :func:`build_fold_config`).
        n_controls_test: Controls at the held-out site (None if labels were
            not provided).
        runnable: Whether the fold meets the minimum-train-sites and
            minimum-per-class requirements. Non-runnable folds are kept in
            the configuration with a reason, never silently omitted.
        skip_reason: Why the fold is not runnable, or None.
    """

    held_out_site: str
    n_train: int
    n_test: int
    n_train_sites: int
    n_cases_test: int | None
    n_controls_test: int | None
    runnable: bool
    skip_reason: str | None


def build_fold_config(
    sites: np.ndarray,
    y: np.ndarray | None = None,
    min_train_sites: int = 2,
    min_per_class: int = 2,
) -> list[FoldSpec]:
    """Enumerate one LOSO fold per site in the dataset.

    Args:
        sites: Site label per subject.
        y: Optional binary labels (1 = case, 0 = control); when given, folds
            whose held-out site has too few cases or controls for effect
            sizes are marked non-runnable up front.
        min_train_sites: Minimum number of training sites required per fold
            (mirrors :class:`loso_replication.loso.LosoReplicator`).
        min_per_class: Minimum cases and controls required at the held-out
            site (mirrors ``loso_replication.loso.effect_sizes``).

    Returns:
        list[FoldSpec]: One spec per unique site, in sorted site order.

    Raises:
        ValueError: If fewer than two sites are present, so a config that
            cannot express any LOSO fold is never written.
    """
    sites = np.asarray(sites)
    unique = np.unique(sites)
    if len(unique) < 2:
        raise ValueError(
            f"LOSO requires at least 2 sites, got {len(unique)}; "
            "refusing to write a fold configuration that holds nothing out."
        )
    y_arr = None if y is None else np.asarray(y)
    specs: list[FoldSpec] = []
    for s in unique:
        test_idx = np.where(sites == s)[0]
        train_idx = np.where(sites != s)[0]
        n_train_sites = int(len(np.unique(sites[train_idx])))
        n_cases = n_controls = None
        if y_arr is not None:
            n_cases = int((y_arr[test_idx] == 1).sum())
            n_controls = int((y_arr[test_idx] == 0).sum())
        runnable = True
        skip_reason = None
        if n_train_sites < min_train_sites:
            runnable = False
            skip_reason = (
                f"only {n_train_sites} training site(s), "
                f"min_train_sites={min_train_sites}"
            )
        elif y_arr is not None and (n_cases < min_per_class or n_controls < min_per_class):
            runnable = False
            skip_reason = (
                f"held-out site has {n_cases} case(s)/{n_controls} control(s), "
                f"need >= {min_per_class} each for effect sizes"
            )
        specs.append(
            FoldSpec(
                held_out_site=str(s),
                n_train=int(len(train_idx)),
                n_test=int(len(test_idx)),
                n_train_sites=n_train_sites,
                n_cases_test=n_cases,
                n_controls_test=n_controls,
                runnable=runnable,
                skip_reason=skip_reason,
            )
        )
    return specs


def write_fold_config(
    specs: list[FoldSpec],
    path: str | Path,
    min_train_sites: int = 2,
    modality: str = "FC",
) -> Path:
    """Serialize a fold configuration to JSON.

    Args:
        specs: The fold specs to write.
        path: Destination file (parent directories are created).
        min_train_sites: The setting the specs were built with.
        modality: Feature modality the configuration applies to.

    Returns:
        Path: The path written.
    """
    payload = {
        "schema": FOLD_CONFIG_SCHEMA,
        "modality": modality,
        "min_train_sites": int(min_train_sites),
        "n_sites": len(specs),
        "n_runnable": int(sum(s.runnable for s in specs)),
        "folds": [asdict(s) for s in specs],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def read_fold_config(path: str | Path) -> list[FoldSpec]:
    """Read a fold configuration written by :func:`write_fold_config`.

    Args:
        path: The fold-config JSON file.

    Returns:
        list[FoldSpec]: The fold specs, in file order.

    Raises:
        ValueError: If the file is missing, malformed, or carries an unknown
            schema tag — a misparsed fold configuration would silently run
            the wrong folds, so it is refused instead.
    """
    path = Path(path)
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Cannot read fold config {path}: {e}") from e
    if not isinstance(payload, dict) or payload.get("schema") != FOLD_CONFIG_SCHEMA:
        raise ValueError(
            f"{path} is not a {FOLD_CONFIG_SCHEMA} fold config; refusing to "
            "guess the format."
        )
    try:
        return [FoldSpec(**f) for f in payload["folds"]]
    except (KeyError, TypeError) as e:
        raise ValueError(f"Malformed fold entry in {path}: {e}") from e
