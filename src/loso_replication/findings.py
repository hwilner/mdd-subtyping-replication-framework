"""Registry of published MDD resting-state connectivity findings.

Each finding is a structured effect spec (feature, expected direction,
source citation) that the LOSO framework can test against harmonized
REST-meta-MDD Phase II features. This is the Paper 1 target list; extend
it via pull request (see CONTRIBUTING.md).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

__all__ = ["Finding", "FINDINGS", "findings_table", "get_finding"]


@dataclass(frozen=True)
class Finding:
    """A published case-control connectivity effect to replicate.

    Attributes:
    ----------
    key:
    Stable identifier, e.g. ``"yan2019_dmn_pcc_hypo"``.
    feature:
    Feature name in the harmonized feature matrix.
    direction:
    Expected sign of the case-control effect: ``+1`` hyper-, ``-1`` hypo-.
    modality:
    Feature modality: ``"FC"``, ``"ALFF"`` or ``"ReHo"``.
    citation:
    Short citation for the source report.
    doi:
    DOI of the source publication.
    """

    key: str
    feature: str
    direction: int
    modality: str
    citation: str
    doi: str


FINDINGS: tuple[Finding, ...] = (
    Finding(
        key="yan2019_dmn_pcc_hypo",
        feature="fc_dmn_pcc_mpfc",
        direction=-1,
        modality="FC",
        citation="Yan et al., 2019, PNAS (REST-meta-MDD)",
        doi="10.1073/pnas.1900390116",
    ),
    Finding(
        key="yan2019_dmn_seed_hypo",
        feature="fc_dmn_seed_wholebrain",
        direction=-1,
        modality="FC",
        citation="Yan et al., 2019, PNAS (REST-meta-MDD)",
        doi="10.1073/pnas.1900390116",
    ),
    Finding(
        key="mulders2015_sgcc_dmn_hyper",
        feature="fc_sgacc_dmn",
        direction=+1,
        modality="FC",
        citation="Mulders et al., 2015, Front. Psychiatry (meta-analysis)",
        doi="10.3389/fpsyt.2015.00144",
    ),
    Finding(
        key="kaiser2015_dmn_hypo",
        feature="fc_dmn_within_network",
        direction=-1,
        modality="FC",
        citation="Kaiser et al., 2015, JAMA Psychiatry (meta-analysis)",
        doi="10.1001/jamapsychiatry.2015.0071",
    ),
    Finding(
        key="kaiser2015_salience_hypo",
        feature="fc_salience_within_network",
        direction=-1,
        modality="FC",
        citation="Kaiser et al., 2015, JAMA Psychiatry (meta-analysis)",
        doi="10.1001/jamapsychiatry.2015.0071",
    ),
    Finding(
        key="tozzi2020_dlpfc_hypo",
        feature="fc_dlpfc_dmn",
        direction=-1,
        modality="FC",
        citation="Tozzi et al., 2020, bioRxiv / REST-meta-MDD Phase II",
        doi="10.1016/j.bpsc.2020.12.016",
    ),
    Finding(
        key="li2013_reho_dmn_altered",
        feature="reho_precuneus",
        direction=-1,
        modality="ReHo",
        citation="Li et al., 2013, J. Affect. Disord.",
        doi="10.1016/j.jad.2013.03.025",
    ),
    Finding(
        key="liu2013_alff_frontal_altered",
        feature="alff_medial_prefrontal",
        direction=-1,
        modality="ALFF",
        citation="Liu et al., 2013, PLoS ONE",
        doi="10.1371/journal.pone.0063481",
    ),
)

_FINDINGS_BY_KEY = {f.key: f for f in FINDINGS}


def get_finding(key: str) -> Finding:
    """Look up a finding by its stable key."""
    try:
        return _FINDINGS_BY_KEY[key]
    except KeyError:
        raise KeyError(f"Unknown finding {key!r}; available: {sorted(_FINDINGS_BY_KEY)}") from None


def findings_table() -> pd.DataFrame:
    """All registered findings as a DataFrame."""
    return pd.DataFrame([asdict(f) for f in FINDINGS])
