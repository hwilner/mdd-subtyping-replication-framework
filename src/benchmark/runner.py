"""Single-fold execution and checksummed per-fold outputs (issue #6).

``run_fold`` executes one leave-one-site-out fold end to end: it
harmonizes the full feature matrix (the same harmonize-then-split contract
as ``scripts/run_loso.py``, documented in docs/METHODS.md), evaluates the
requested held-out site with the same primitives as
:class:`loso_replication.loso.LosoReplicator`, and returns a structured,
JSON-serializable record. ``write_fold_output`` and ``write_manifest``
store per-fold records with SHA-256 checksums so a batch execution
(issue #9) can verify the collected results set.

The fold math intentionally mirrors ``LosoReplicator.run``'s loop body;
``tests/test_benchmark.py`` pins the two implementations to exact
agreement and pins the demo fold outputs to the committed
``reports/loso/loso_fold_metrics.csv`` numbers, so any drift fails loudly.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

from loso_replication.combat import combat
from loso_replication.loso import effect_sizes

__all__ = [
    "FOLD_RESULT_SCHEMA",
    "MANIFEST_SCHEMA",
    "evaluate_fold",
    "fold_filename",
    "run_fold",
    "sha256_file",
    "verify_manifest",
    "write_fold_output",
    "write_manifest",
]

#: Schema tags for the per-fold result and the manifest, so future readers
#: detect format changes instead of misparsing them.
FOLD_RESULT_SCHEMA = "loso-fold-result/v1"
MANIFEST_SCHEMA = "loso-fold-manifest/v1"


def evaluate_fold(
    held_out_site: str,
    X_h: np.ndarray,
    y: np.ndarray,
    sites: np.ndarray,
    alpha: float = 0.05,
    min_train_sites: int = 2,
) -> dict:
    """Evaluate one LOSO fold on an already-harmonized matrix.

    Mirrors the loop body of ``LosoReplicator.run``: sites that cannot meet
    ``min_train_sites`` or lack the cases/controls for effect sizes produce
    a ``skipped`` record with a reason rather than an exception, and metrics
    that are undefined (no training-significant effect, or a zero-variance
    effect map) are recorded as None with the reason preserved.

    Args:
        held_out_site: The site to hold out.
        X_h: (n_samples, n_features) harmonized feature matrix.
        y: Binary labels, 1 = case (MDD), 0 = control.
        sites: Site label per sample.
        alpha: Nominal p-value threshold for "significant" effects.
        min_train_sites: Minimum number of training sites required.

    Returns:
        dict: A fold record with ``status`` "completed" or "skipped".

    Raises:
        ValueError: If ``held_out_site`` is not present in ``sites`` — a
            typo'd fold name must fail loudly, not skip silently.
    """
    X_h = np.asarray(X_h, dtype=float)
    y = np.asarray(y)
    sites = np.asarray(sites)
    test_idx = np.where(sites == held_out_site)[0]
    if len(test_idx) == 0:
        raise ValueError(
            f"Held-out site {held_out_site!r} not present; available sites: "
            f"{[str(s) for s in np.unique(sites)]}"
        )
    train_idx = np.where(sites != held_out_site)[0]
    record = {
        "held_out_site": str(held_out_site),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "n_cases_test": int((y[test_idx] == 1).sum()),
        "n_controls_test": int((y[test_idx] == 0).sum()),
    }
    n_train_sites = len(np.unique(sites[train_idx]))
    if n_train_sites < min_train_sites:
        record.update(
            status="skipped",
            skip_reason=(
                f"only {n_train_sites} training site(s), "
                f"min_train_sites={min_train_sites}"
            ),
        )
        return record
    try:
        d_train, p_train = effect_sizes(X_h[train_idx], y[train_idx])
        d_test, p_test = effect_sizes(X_h[test_idx], y[test_idx])
    except ValueError as e:
        record.update(status="skipped", skip_reason=str(e))
        return record

    sig_train = p_train < alpha
    n_sig = int(sig_train.sum())
    if n_sig == 0:
        sign_cons = held_sig = None
        undefined_reason = "no training effect significant at alpha"
    else:
        sign_cons = float(
            np.mean(np.sign(d_train[sig_train]) == np.sign(d_test[sig_train]))
        )
        held_sig = float(np.mean(p_test[sig_train] < alpha))
        undefined_reason = None
    corr = float(np.corrcoef(d_train, d_test)[0, 1])
    if not math.isfinite(corr):
        corr = None
        undefined_reason = "effect map has no variance"
    record.update(
        status="completed",
        skip_reason=None,
        alpha=float(alpha),
        n_train_significant_effects=n_sig,
        sign_consistency=sign_cons,
        effect_map_correlation=corr,
        heldout_significance=held_sig,
        undefined_reason=undefined_reason,
    )
    return record


def fold_filename(held_out_site: str) -> str:
    """Filename for a fold record; non-alphanumerics become underscores.

    Args:
        held_out_site: The held-out site label.

    Returns:
        str: A filesystem-safe file name like ``fold_site_0.json``.
    """
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(held_out_site))
    return f"fold_{safe}.json"


def run_fold(
    held_out_site: str,
    X: np.ndarray,
    y: np.ndarray,
    sites: np.ndarray,
    alpha: float = 0.05,
    min_train_sites: int = 2,
    harmonize=combat,
    modality: str = "FC",
    provenance: dict | None = None,
) -> dict:
    """Run one LOSO fold end to end and return a JSON-serializable record.

    Args:
        held_out_site: The site to hold out.
        X: (n_samples, n_features) raw (pre-harmonization) feature matrix.
        y: Binary labels, 1 = case (MDD), 0 = control.
        sites: Site label per sample.
        alpha: Nominal p-value threshold for "significant" effects.
        min_train_sites: Minimum number of training sites required.
        harmonize: Callable ``(X, sites) -> X_harmonized`` applied to the
            full matrix before splitting (default: built-in ComBat, matching
            ``scripts/run_loso.py``); pass None to skip harmonization.
        modality: Feature modality recorded in the output.
        provenance: Optional dict (e.g. data root and synthetic flag read
            from ``STAGING_REPORT.json``) embedded verbatim. Never guessed.

    Returns:
        dict: The fold record, ready for :func:`write_fold_output`.
    """
    X = np.asarray(X, dtype=float)
    if harmonize is not None:
        X_h = np.asarray(harmonize(X, sites), dtype=float)
        harmonization = "combat (built-in empirical Bayes)"
    else:
        X_h = X
        harmonization = "none"
    record = evaluate_fold(
        held_out_site, X_h, y, sites, alpha=alpha, min_train_sites=min_train_sites
    )
    record = {
        "schema": FOLD_RESULT_SCHEMA,
        "modality": modality,
        "harmonization": harmonization,
        "provenance": provenance,
        **record,
    }
    return record


def _strict_json(record: dict) -> str:
    """Serialize a record deterministically, refusing non-JSON float tokens.

    Args:
        record: The fold record or manifest to serialize.

    Returns:
        str: The JSON text (sorted keys, trailing newline).

    Raises:
        ValueError: On NaN/inf values — undefined metrics must be recorded
            as None, because a NaN literal is not valid JSON and would make
            the checksummed results set unparsable by strict readers.
    """
    return json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n"


def write_fold_output(record: dict, results_dir: str | Path) -> Path:
    """Write one fold record under ``results_dir/folds/<modality>/``.

    Args:
        record: A record from :func:`run_fold`.
        results_dir: The benchmark results directory (e.g. ``reports/loso``).

    Returns:
        Path: The path written.
    """
    out_dir = Path(results_dir) / "folds" / str(record.get("modality", "FC"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / fold_filename(record["held_out_site"])
    path.write_text(_strict_json(record))
    return path


def sha256_file(path: str | Path) -> str:
    """SHA-256 hex digest of a file's bytes.

    Args:
        path: The file to hash.

    Returns:
        str: The hex digest.
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_manifest(results_dir: str | Path, modality: str = "FC") -> Path:
    """Write a SHA-256 manifest over the per-fold records of one modality.

    Args:
        results_dir: The benchmark results directory.
        modality: The modality subdirectory under ``folds/``.

    Returns:
        Path: The manifest path written.

    Raises:
        FileNotFoundError: If no fold records exist — an empty manifest
            would look like a completed-but-empty results set.
    """
    fold_dir = Path(results_dir) / "folds" / modality
    files = sorted(fold_dir.glob("fold_*.json"))
    if not files:
        raise FileNotFoundError(f"No fold records in {fold_dir}")
    entries = []
    for f in files:
        rec = json.loads(f.read_text())
        entries.append(
            {
                "file": f.name,
                "held_out_site": rec["held_out_site"],
                "status": rec["status"],
                "sha256": sha256_file(f),
            }
        )
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "modality": modality,
        "n_folds": len(entries),
        "n_completed": int(sum(e["status"] == "completed" for e in entries)),
        "n_skipped": int(sum(e["status"] == "skipped" for e in entries)),
        "folds": entries,
    }
    path = fold_dir / "manifest.json"
    path.write_text(_strict_json(manifest))
    return path


def verify_manifest(results_dir: str | Path, modality: str = "FC") -> list[str]:
    """Check every manifest entry against the bytes on disk.

    Args:
        results_dir: The benchmark results directory.
        modality: The modality subdirectory under ``folds/``.

    Returns:
        list[str]: Descriptions of missing/altered files; empty if the
        results set verifies. Callers decide how to report failures.
    """
    fold_dir = Path(results_dir) / "folds" / modality
    manifest = json.loads((fold_dir / "manifest.json").read_text())
    if manifest.get("schema") != MANIFEST_SCHEMA:
        return [f"{fold_dir}/manifest.json: unknown schema {manifest.get('schema')!r}"]
    problems = []
    listed = set()
    for entry in manifest["folds"]:
        listed.add(entry["file"])
        f = fold_dir / entry["file"]
        if not f.exists():
            problems.append(f"missing fold file {f}")
        elif sha256_file(f) != entry["sha256"]:
            problems.append(f"checksum mismatch for {f}")
    for f in sorted(fold_dir.glob("fold_*.json")):
        if f.name not in listed:
            problems.append(f"unlisted fold file {f}")
    return problems
