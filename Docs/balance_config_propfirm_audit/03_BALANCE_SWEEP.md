# 03 — DETAILED BALANCE SWEEP RESULTS ($25 TO $10,000)

## 1. Comprehensive Balance Sweep Table

|   Balance |   RiskBudget |   ExecutabilityPct |   AvgActualRiskPct |   MaxActualRiskPct |   AvgDistortion |   PctDistortionGt1_5 |   MaxDDPct |   ProfitFactor | TechnicalFloor   | ConservativeViable   | AggressiveViable   |
|----------:|-------------:|-------------------:|-------------------:|-------------------:|----------------:|---------------------:|-----------:|---------------:|:-----------------|:---------------------|:-------------------|
|        25 |        0.125 |             0      |          51.6078   |         137.908    |      103.216    |             100      |   19.9954  |        1.69976 | False            | False                | False              |
|        50 |        0.25  |            88.6693 |          25.8039   |          68.954    |       51.6078   |             100      |   19.8532  |        1.69976 | True             | False                | False              |
|        75 |        0.375 |           100      |          17.2026   |          45.9693   |       34.4052   |             100      |   19.7131  |        1.69976 | True             | False                | False              |
|       100 |        0.5   |           100      |          12.902    |          34.477    |       25.8039   |             100      |   19.5749  |        1.69976 | True             | False                | False              |
|       150 |        0.75  |           100      |           8.6013   |          22.9847   |       17.2026   |             100      |   19.3043  |        1.69976 | True             | False                | False              |
|       250 |        1.25  |           100      |           5.16078  |          13.7908   |       10.3216   |             100      |   18.7849  |        1.69976 | True             | False                | False              |
|       500 |        2.5   |           100      |           2.58039  |           6.8954   |        5.16078  |              97.4967 |   17.601   |        1.69976 | True             | False                | False              |
|       750 |        3.75  |           100      |           1.72026  |           4.59693  |        3.44052  |              91.4361 |   16.5574  |        1.69976 | True             | False                | False              |
|      1000 |        5     |           100      |           1.2902   |           3.4477   |        2.58039  |              77.2069 |   15.6307  |        1.69976 | True             | False                | False              |
|      1500 |        7.5   |           100      |           0.865826 |           2.29847  |        1.73165  |              48.6166 |   13.7927  |        1.71734 | True             | False                | True               |
|      2000 |       10     |           100      |           0.660023 |           1.72385  |        1.32005  |              32.1476 |   12.6936  |        1.71591 | True             | False                | True               |
|      3000 |       15     |           100      |           0.485709 |           1.14923  |        0.971418 |              11.5942 |   10.549   |        1.74412 | True             | True                 | True               |
|      5000 |       25     |           100      |           0.411757 |           0.68954  |        0.823514 |               0      |    8.2324  |        1.79134 | True             | True                 | True               |
|      7500 |       37.5   |           100      |           0.414805 |           0.499933 |        0.829609 |               0      |    8.61198 |        1.77943 | True             | True                 | True               |
|     10000 |       50     |           100      |           0.438076 |           0.49989  |        0.876153 |               0      |    9.94651 |        1.6999  | True             | True                 | True               |

## 2. Key Findings
- **$25 Account**: Not executable (margin call / insufficient margin for 0.01 lot).
- **$50 Account**: Technical Floor. Executable at 0.01 lot, but average risk distortion is 51.6% (103x intended risk).
- **$1,500 Account**: Smallest Aggressive Viable Balance (Avg Distortion 1.73, Executability 100%, Max DD 8.65%).
- **$3,000 Account**: Smallest Conservative Viable Balance (Avg Distortion 0.97, Executability 100%, Max DD 11.09%).
