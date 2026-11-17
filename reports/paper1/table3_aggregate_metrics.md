**Table 3. Aggregate LOSO benchmark results.** Means are over the folds for which each metric is defined; the values are deterministic for the committed synthetic seed and protected from silent drift by `make check-repro`. *Synthetic demonstration of the benchmark pipeline — not an MDD finding. Real-data tables remain blocked on DUA access (issue #2).*

| Metric | Mean | Defined folds | Interpretation |
|---|---:|---:|---|
| Sign consistency | 0.760 | 6/6 | Fraction of training-significant effects with the same direction at the held-out site |
| Effect map correlation | 0.585 | 6/6 | Pearson correlation between train and held-out Cohen's d maps |
| Heldout significance | 0.895 | 6/6 | Fraction of training-significant effects that are nominally significant at the held-out site |
