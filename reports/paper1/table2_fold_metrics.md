**Table 2. Per-fold leave-one-site-out replication metrics.** Each row holds out one site, estimates case-control effects on the remaining sites, and scores replication on the unseen site. Source: `reports/loso/loso_fold_metrics.csv`. *Synthetic demonstration of the benchmark pipeline — not an MDD finding. Real-data tables remain blocked on DUA access (issue #2).*

| Held-out site | Train n | Test n | Sign consistency | Effect-map correlation | Held-out significance |
|---|---:|---:|---:|---:|---:|
| site_0 | 200 | 40 | 0.667 | 0.570 | 0.905 |
| site_1 | 200 | 40 | 0.750 | 0.568 | 0.812 |
| site_2 | 200 | 40 | 0.722 | 0.597 | 0.944 |
| site_3 | 200 | 40 | 0.833 | 0.633 | 0.944 |
| site_4 | 200 | 40 | 0.824 | 0.639 | 0.824 |
| site_5 | 200 | 40 | 0.765 | 0.499 | 0.941 |
