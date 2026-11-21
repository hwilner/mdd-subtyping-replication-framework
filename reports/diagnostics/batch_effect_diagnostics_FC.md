# Batch-effect diagnostics (pre/post ComBat)

Scope: synthetic demonstration — validates the diagnostics machinery, not an MDD finding. Data root `data/demo`, modality FC; harmonization: combat (built-in empirical Bayes).

**Table D1. Site-signal diagnostics before vs. after harmonization.** Site eta^2 is the per-feature fraction of variance explained by site; site classification is the cross-validated accuracy of predicting site from the features (chance = largest site fraction); site-mean spread is the SD of per-site feature means. All three should fall after ComBat.

| Diagnostic | Pre-ComBat | Post-ComBat |
|---|---:|---:|
| Site eta^2 (mean over features) | 0.1845 | 0.0034 |
| Site eta^2 (max over features) | 0.4186 | 0.0100 |
| Site classification accuracy | 0.9917 | 0.0167 |
| Chance (majority site fraction) | 0.1667 | 0.1667 |
| Site-mean spread (mean over features) | 0.5634 | 0.0678 |

**Table D2. Biological-signal preservation.** The case-control Cohen's d effect map before vs. after harmonization; a high correlation and few sign flips mean ComBat removed batch signal without removing the biological covariate signal.

| Quantity | Value |
|---|---:|
| Effect-map correlation (pre vs. post) | 0.9900 |
| Mean |d| pre-ComBat | 0.3966 |
| Mean |d| post-ComBat | 0.4161 |
| Sign flips | 7 / 60 |
