# Introduction — MDD Subtyping Replication Framework

**Series note:** This is **Paper 1 of 3** in the MDD subtyping series. It is the **foundation paper**: it builds the harmonized REST-meta-MDD Phase II dataset and the replication-analysis framework that Paper 2 (`mdd-connectivity-subtypes`) and Paper 3 (`mdd-ssri-response-prediction`) directly reuse.

## Background

Major depressive disorder (MDD) is one of the most common and disabling psychiatric conditions worldwide, yet its pathophysiology remains poorly understood. A central obstacle is heterogeneity: two patients meeting the same diagnostic criteria may differ profoundly in symptom profile, course, treatment response, and — presumably — neurobiology. Case–control studies that average across this heterogeneity risk detecting effects that describe no individual patient, motivating a move toward data-driven subtyping ("biotyping") of depression.

Resting-state functional MRI (R-fMRI) has become the dominant modality for probing the brain's intrinsic functional organization in MDD. Functional connectivity (FC) studies, usually of the default mode network (DMN), frontoparietal control, limbic, and attention networks, have produced a rich but inconsistent literature. Meta-analyses converge on distributed network dysfunction in MDD, with altered DMN and frontoparietal connectivity [2], yet the direction and locus of effects vary across studies, likely reflecting small samples, analytic flexibility, and site/scanner heterogeneity [1][5].

The field has been shaped by a high-profile controversy. Drysdale et al. (2017) used resting-state connectivity to define four neurophysiological "biotypes" of depression that purportedly predicted response to repetitive transcranial magnetic stimulation [3]. The result attracted enormous attention, but a methodological replication by Dinga et al. (2019) in an independent sample found that the canonical correlations and the cluster structure were not statistically significant once appropriate statistical tests were applied, arguing that the evidence for connectivity-defined depression biotypes is weak [4]. This episode crystallized a broader reproducibility crisis in predictive neuroimaging: Varoquaux (2018) demonstrated analytically and empirically that cross-validation error bars at typical neuroimaging sample sizes are enormous, so modest single-cohort results can be wildly optimistic [5].

The REST-meta-MDD Project, organized by the DIRECT consortium, was created to address exactly this problem [1][8]. Twenty-five research groups in China contributed R-fMRI data preprocessed locally with a standardized protocol and shared as derived indices (ALFF, ReHo, FC matrices), enabling large-scale mega-analysis while protecting privacy. The Phase I paper (1,300 MDD patients, 1,128 controls) found reduced — not increased — DMN connectivity in recurrent MDD, showing how large, harmonized samples can overturn conclusions from smaller studies [1]. REST-meta-MDD Phase II (~2,400 subjects, ~25 sites) extends this resource with harmonized resting-state fMRI and richer phenotyping [8], offering a rare testbed for studying cross-site reproducibility itself.

Two methodological developments are central to this paper. First, harmonization: ComBat, an empirical Bayes batch-adjustment method imported from genomics, effectively removes scanner/site effects from multi-site MRI features while preserving biological variance of interest [6]. Second, honest evaluation: leave-one-site-out (LOSO) cross-validation, in which all discovery is performed on N−1 sites and testing on the fully held-out site, provides a far more realistic estimate of generalization than random-fold cross-validation and is increasingly considered the minimum standard for multi-site neuroimaging claims.

## Prior work and gap

Prior multi-site efforts have either meta-analyzed published peaks [2] or pooled raw data without systematic quantification of site effects [3]. The REST-meta-MDD Phase I analyses modeled site as a covariate but did not benchmark how well individual published connectivity findings replicate across sites, nor how harmonization choices change replication rates. Meanwhile, the biotyping literature has largely ignored cross-site validation entirely, with the Drysdale/Dinga controversy [3][4] illustrating the consequences. What is missing is a rigorous, open framework that (i) quantifies cross-site non-replication of canonical MDD connectivity findings, (ii) measures residual batch effects after ComBat harmonization, and (iii) supplies a reproducible LOSO benchmark on which downstream subtype discovery and treatment-prediction claims can be honestly evaluated.

## Research questions

1. How well do published MDD connectivity findings (e.g., DMN hypo/hyperconnectivity, frontoparietal alterations) replicate across the ~25 REST-meta-MDD Phase II sites?
2. How much residual site/scanner batch effect remains after ComBat harmonization, and how sensitive are replication conclusions to harmonization choices?
3. What leave-one-site-out benchmark protocol gives an honest estimate of cross-site generalization for the downstream subtype and prediction papers in this series?

## Data

| Dataset | Size | Content | Access |
| --- | --- | --- | --- |
| REST-meta-MDD Phase II | ~2,400 subjects, ~25 sites | Preprocessed resting-state fMRI derivatives (ALFF/ReHo/FC matrices) + phenotypes | DUA via R-fMRI Maps Project [8] |

## Methods

- Ingestion and QC of REST-meta-MDD Phase II derived indices; exclusion rules mirroring the consortium protocol (head motion, coverage, preprocessing residuals) [1].
- Cross-site harmonization of connectivity features with ComBat, with covariate protection of age, sex, and diagnostic effects [6]; comparison against unharmonized and within-site standardized baselines.
- Replication battery: a preregistered set of published MDD connectivity findings (DMN within-network FC, DMN–frontoparietal coupling, limbic–cortical edges) tested per site, with effect-size concordance and sign-consistency metrics.
- Leave-one-site-out replication framework: discovery on N−1 sites, evaluation on the held-out site, iterated over all sites; uncertainty quantified per Varoquaux [5].
- Synthetic-data unit tests with known site effects and known effect sizes to validate the framework's calibration before it is applied to real data.

## Expected contributions

- A harmonized, QC'd REST-meta-MDD Phase II connectivity resource with documented batch-effect diagnostics and code.
- An empirical map of which canonical MDD connectivity findings do and do not replicate across sites, contextualizing the entire series.
- An open leave-one-site-out replication-benchmark framework (code + scoring rules) reused by Paper 2 (`mdd-connectivity-subtypes`) for subtype validation and by Paper 3 (`mdd-ssri-response-prediction`) for treatment-response prediction.

## Scope and boundary

- No new subtype discovery here (that is Paper 2); no treatment-response prediction (that is Paper 3).
- Only resting-state fMRI from REST-meta-MDD; no external cohorts, no task fMRI, no structural MRI endpoints in this paper.
- We do not claim new disease biology; the contribution is measurement and methodology — establishing what is reproducible before attempting to explain it.

## References

1. Yan C-G, Chen X, Li L, et al. Reduced default mode network functional connectivity in patients with recurrent major depressive disorder. *Proceedings of the National Academy of Sciences* 2019;116(18):9078–9083. doi:10.1073/pnas.1900390116
2. Kaiser RH, Andrews-Hanna JR, Wager TD, Pizzagalli DA. Large-scale network dysfunction in major depressive disorder: a meta-analysis of resting-state functional connectivity. *JAMA Psychiatry* 2015;72(6):603–611. doi:10.1001/jamapsychiatry.2015.0071
3. Drysdale AT, Grosenick L, Downar J, et al. Resting-state connectivity biomarkers define neurophysiological subtypes of depression. *Nature Medicine* 2017;23(1):28–38. doi:10.1038/nm.4246 (PMID: 27918562)
4. Dinga R, Schmaal L, Penninx BWH, et al. Evaluating the evidence for biotypes of depression: methodological replication and extension of Drysdale et al. (2017). *NeuroImage: Clinical* 2019;22:101796. doi:10.1016/j.nicl.2019.101796
5. Varoquaux G. Cross-validation failure: small sample sizes lead to large error bars. *NeuroImage* 2018;180:68–77. doi:10.1016/j.neuroimage.2017.06.061
6. Fortin J-P, Cullen N, Sheline YI, et al. Harmonization of cortical thickness measurements across scanners and sites. *NeuroImage* 2018;167:104–120. doi:10.1016/j.neuroimage.2017.11.024
7. Marquand AF, Rezek I, Buitelaar J, Beckmann CF. Understanding heterogeneity in clinical cohorts using normative models: beyond case–control studies. *Biological Psychiatry* 2016;80(7):552–561. doi:10.1016/j.biopsych.2015.12.023
8. Chen X, Lu B, Li H-X, et al. The DIRECT consortium and the REST-meta-MDD project: towards neuroimaging biomarkers of major depressive disorder. *Psychoradiology* 2022;2(1):32–42. doi:10.1093/psyrad/kkac005
9. Varol E, Sotiras A, Davatzikos C. HYDRA: revealing heterogeneity of imaging and genetic patterns through a multiple max-margin discriminative analysis framework. *NeuroImage* 2017;145:346–364. doi:10.1016/j.neuroimage.2016.02.041
