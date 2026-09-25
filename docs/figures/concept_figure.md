# Concept figure — MDD Subtyping Replication Framework

**Caption:** The replication pipeline. Resting-state fMRI connectivity features from ~25 scanning sites are harmonized with ComBat (site-specific shifts removed, biology preserved); then a leave-one-site-out (LOSO) loop discovers effects on N−1 sites and tests them on the hidden site; replication is scored by sign consistency, effect-map correlation, and held-out significance, producing an open, reusable benchmark for subtype-validation and treatment-prediction studies.

```mermaid
flowchart LR
    subgraph D["Multi-site resting-state fMRI"]
        S1["Site 1"] & S2["Site 2"] & SN["... Site 25"]
    end
    D --> CB["ComBat harmonization<br/>remove site shifts"]
    CB --> LV["LOSO cross-validation<br/>hide one site per round"]
    LV --> RM["Replication metrics<br/>sign · map correlation · significance"]
    RM --> RB["Reusable benchmark for<br/>subtyping & prediction papers"]
```

*A rendered PNG concept figure was generated for this repository; because binary assets cannot be committed through the tooling used for this update, this file carries the faithful Mermaid source of the same diagram.*
