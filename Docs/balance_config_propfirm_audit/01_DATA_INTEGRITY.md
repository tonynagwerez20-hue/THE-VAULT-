# 01 — DATA INTEGRITY AND DEDUPLICATION AUDIT

## 1. Trade Dataset Audit Summary

| Metric | Raw Trade CSV | Reconciled Ground Truth | Position Ledger 759 |
| --- | ---: | ---: | ---: |
| **Total Rows** | 1,260 | 765 | 759 |
| **Unique Trade IDs** | 793 | 765 | 759 |
| **Exact Duplicate Rows** | 61 | 0 | 0 |
| **Conflicting Duplicate Rows** | 152 | 0 | 0 |
| **Data Integrity Status** | Contaminated | Reconciled | **CANONICAL GROUND TRUTH** |

## 2. Integrity Checks Conducted
- [x] Unique trade ID validation
- [x] Timestamp sanity check (entry < exit)
- [x] Price & Stop Distance validity (SL distance > 0)
- [x] Volume consistency (0.01 lot step enforcement)
- [x] P/L math reconciliation ($1.00 per point on 0.01 lot)
