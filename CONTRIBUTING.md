# Contributing

Thanks for helping build the MDD subtyping-with-replication framework
(Paper 1 of the series). This repository is developed in the open; all
changes land via pull request.

## Ground rules

- **No real data in the repo.** REST-meta-MDD Phase II data are DUA-restricted
  (see `docs/DATA_ACCESS.md`). Never commit subject-level data, credentials,
  or derived features from the real dataset. Synthetic data only.
- **Tests must pass.** `python -m pytest -q` must be green before merge.
  CI runs pytest on Python 3.10–3.12.
- **Small, reviewable PRs.** One task issue per PR where possible; reference
  the issue (`Closes #N`) in the PR body.

## Development setup

```bash
git clone https://github.com/hwilner/mdd-subtyping-replication-framework.git
cd mdd-subtyping-replication-framework
pip install -e ".[dev]"
python -m pytest -q
```

`neuroCombat` is an optional dependency (`pip install -e ".[neurocombat]"`);
when absent, the built-in empirical-Bayes ComBat in
`src/loso_replication/combat.py` is used. Both paths are covered by tests.

## Project layout

| Path | Contents |
|---|---|
| `src/loso_replication/combat.py` | ComBat harmonization (EB, with optional neuroCombat backend). |
| `src/loso_replication/loso.py` | LOSO splitting, effect sizes, replication metrics. |
| `src/loso_replication/findings.py` | Registry of published MDD connectivity findings. |
| `src/loso_replication/simulate.py` | Synthetic multi-site data with planted ground truth. |
| `src/loso_replication/io.py` | REST-meta-MDD Phase II loaders (DUA-gated). |
| `tests/` | Synthetic validation of the full pipeline. |
| `docs/` | Introduction and data-access documentation. |

## Adding a published finding to the registry

1. Add a `Finding` entry in `src/loso_replication/findings.py` with a stable
   key, feature name, expected direction, modality, citation and DOI.
2. Keep `test_findings_registry_wellformed` green.
3. Explain in the PR why the finding is in scope for the Paper 1 benchmark.

## Issue workflow

Task issues carry a `<!-- task-key: ... -->` marker and acceptance criteria.
Pick one up by commenting, open a PR referencing it, and close it only when
every acceptance criterion is met (or explicitly descoped in the issue).
