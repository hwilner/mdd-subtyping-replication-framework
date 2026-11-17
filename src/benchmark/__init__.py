"""Config-driven LOSO benchmark runner (issue #6).

This package turns the leave-one-site-out benchmark into fold-addressable
infrastructure: a fold configuration enumerates one fold per site in the
staged dataset, and each fold can be executed independently (e.g. as one
element of a job array) writing a structured, checksummed per-fold output.

The pipeline contract is identical to ``scripts/run_loso.py``: ComBat
harmonization is applied to the full feature matrix before splitting
(see docs/METHODS.md, "Harmonization pitfalls"), and the fold math reuses
the same primitives as :class:`loso_replication.loso.LosoReplicator`.
``tests/test_benchmark.py`` pins single-fold outputs to exact agreement
with both the full-run replicator and the committed demo benchmark numbers.

Real-data use remains gated by the REST-meta-MDD Phase II DUA (issue #2);
all committed outputs of this package are from the synthetic demo dataset.
"""

from .folds import FoldSpec, build_fold_config, read_fold_config, write_fold_config
from .runner import (
    evaluate_fold,
    run_fold,
    sha256_file,
    verify_manifest,
    write_fold_output,
    write_manifest,
)

__all__ = [
    "FoldSpec",
    "build_fold_config",
    "read_fold_config",
    "write_fold_config",
    "evaluate_fold",
    "run_fold",
    "sha256_file",
    "verify_manifest",
    "write_fold_output",
    "write_manifest",
]
