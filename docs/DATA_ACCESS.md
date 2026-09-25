# Data access: REST-meta-MDD Phase II

All real-data work in this repository (harmonization QC, the LOSO benchmark
on real data, and the writeup) is **blocked** until the REST-meta-MDD
Phase II Data Use Agreement (DUA) is approved. The data are **not** and must
**never** be committed to this repository.

## Source

REST-meta-MDD Phase II is distributed through the **R-fMRI Maps Project**
(DPARSF/DPABI ecosystem, Yan lab):

- Portal: <http://rfmri.org/REST-meta-MDD>
- Phase I reference: Yan et al., 2019, *PNAS*
  (<https://doi.org/10.1073/pnas.1900390116>) — reduced default mode network
  connectivity in MDD, the flagship finding this framework attempts to
  replicate site-by-site.
- Phase II: ~2,400 participants across ~25 scanning sites with raw data and
  standardized preprocessed derivatives (FC, ALFF, ReHo feature maps).

## Steps to obtain access

1. **Read the terms** on the R-fMRI Maps Project REST-meta-MDD page,
   including publication/acknowledgement requirements and the prohibition on
   redistribution.
2. **Prepare the application**: applicant name, institutional affiliation,
   institutional email, brief project description (cite this repository and
   the project goal: harmonization resource + LOSO replication benchmark).
3. **Submit the DUA** via the R-fMRI Maps Project portal and record the
   submission date in issue `mdd-p1-dua-access`.
4. **Track approval**; response typically takes days to a few weeks.
5. **On approval**: store download credentials securely (institutional
   password manager — never in git), download the derivatives, and place
   them in a local data root outside the repository, e.g.:

   ```text
   $DATA_ROOT/
     phenotypes.csv        # subject, site, diagnosis (1=MDD, 0=HC)
     features_fc.csv       # subjects x features (functional connectivity)
     features_alff.csv     # subjects x features
     features_reho.csv     # subjects x features
   ```

   `loso_replication.io.load_dataset(data_root)` expects exactly this layout.
6. **Summarize the approved data-usage terms** in this file (allowed uses,
   acknowledgement text, redistribution limits) to complete the
   `mdd-p1-dua-access` acceptance criteria.

## What is blocked on the DUA

| Task issue | Blocked work |
|---|---|
| `mdd-p1-harmonization` | ComBat on real FC/ALFF/ReHo features; motion/preprocessing QC; batch-effect diagnostics under `reports/`. |
| `mdd-p1-loso-benchmark` | LOSO replication benchmark across ~25 real sites; figures/tables under `reports/loso/`. |
| `mdd-p1-writeup` | Results sections and release of the benchmarked framework. |

What is **not** blocked: the replication framework itself, the ComBat
implementation, and the synthetic validation suite — all delivered and
tested without real data (`python -m pytest -q`).
