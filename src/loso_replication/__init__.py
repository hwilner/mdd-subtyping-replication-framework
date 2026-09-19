"""LOSO replication framework for MDD resting-state connectivity findings.

Paper 1 of the MDD subtyping series: ComBat harmonization of
REST-meta-MDD Phase II features plus a leave-one-site-out replication
benchmark for published case-control connectivity findings.

Quick start (synthetic data)::

    from loso_replication import simulate_multisite, combat, LosoReplicator

    ds = simulate_multisite(seed=0)
    X_h = combat(ds.X, ds.sites)
    result = LosoReplicator().run(X_h, ds.y, ds.sites)
    print(result.summary())

Module overview
---------------
- :mod:`loso_replication.combat` — empirical-Bayes ComBat harmonization.
- :mod:`loso_replication.loso` — LOSO splitting, effect sizes, replication
  metrics (sign consistency, effect-map correlation, held-out significance).
- :mod:`loso_replication.findings` — registry of published MDD findings.
- :mod:`loso_replication.simulate` — synthetic multi-site data with
  planted biological and batch effects.
- :mod:`loso_replication.io` — REST-meta-MDD Phase II loaders (require DUA).
"""

from .combat import CombatHarmonizer, combat
from .findings import FINDINGS, Finding, findings_table, get_finding
from .io import DataAccessError, load_dataset, load_features, load_phenotypes
from .loso import LosoReplicator, LosoResult, FoldResult, effect_sizes
from .simulate import SyntheticDataset, simulate_multisite

__version__ = "0.1.0"

__all__ = [
    "combat",
    "CombatHarmonizer",
    "effect_sizes",
    "FoldResult",
    "LosoResult",
    "LosoReplicator",
    "Finding",
    "FINDINGS",
    "findings_table",
    "get_finding",
    "SyntheticDataset",
    "simulate_multisite",
    "DataAccessError",
    "load_features",
    "load_phenotypes",
    "load_dataset",
]
