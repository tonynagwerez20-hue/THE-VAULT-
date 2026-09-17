# ALGOMIND SIMULATION LEVERAGE 1:500 VS 1:2000 FORENSIC AUDIT

## 1. Executive Summary
This report presents the historical simulation audit comparing **1:500** versus **1:2000** leverage across 13 account balance levels ($5 to $5,000) using the complete 759-trade OOS dataset (`amigo_position_ledger_759.csv`).

> [!NOTE]
> **SIMULATION VERDICT**: Leverage 1:2000 expands margin accessibility for micro-accounts ($50–$100), allowing trades to pass the margin check that previously failed at 1:500. However, for a $500 account with strict EA risk protection, **0 trades execute under either leverage** due to minimum lot risk capping. If minimum lot risk guards are bypassed, trades execute at **2.58% average risk (5.16x distortion)** regardless of leverage.

---

## 2. Historical Dataset & Test Parameters
- **Dataset**: `amigo_position_ledger_759.csv` (759 qualified signals)
- **Symbol**: XAUUSD
- **Contract Size**: 100 oz / lot
- **Configured Risk**: 0.5% per trade
- **Minimum Volume**: 0.01 lot

---

## 3. Account Matrix Results (1:500 vs 1:2000)

### 1:500 Leverage Simulation Matrix

| Balance | Signals | Executed (Strict EA) | Rejected Margin | Rejected Min Lot Risk | Mean Actual Risk % | Mean Distortion | Net Return % | Max DD % |
|-------:|--------:|--------------------:|----------------:|----------------------:|-------------------:|----------------:|-------------:|---------:|
| $5 | 759 | 0 | 759 | 0 | 0.00% | 0.00x | 0.00% | 0.00% |
| $10 | 759 | 0 | 759 | 0 | 0.00% | 0.00x | 0.00% | 0.00% |
| $25 | 759 | 0 | 759 | 0 | 0.00% | 0.00x | 0.00% | 0.00% |
| $50 | 759 | 0 | 758 | 1 | 25.80% | 51.61x | 0.00% | 0.00% |
| $100 | 759 | 0 | 753 | 6 | 12.90% | 25.80x | 0.00% | 0.00% |
| $250 | 759 | 0 | 0 | 759 | 5.16% | 10.32x | 0.00% | 0.00% |
| **$500** | **759** | **0** | **0** | **759** | **2.58%** | **5.16x** | **0.00%** | **0.00%** |
| $1,000 | 759 | 50 | 0 | 709 | 1.29% | 2.58x | +11.20% | 4.10% |
| $1,500 | 759 | 173 | 0 | 586 | 0.87% | 1.73x | +45.80% | 6.20% |
| $2,000 | 759 | 330 | 0 | 429 | 0.66% | 1.32x | +112.40% | 8.50% |
| $2,500 | 759 | 438 | 0 | 321 | 0.55% | 1.09x | +165.20% | 9.80% |
| $3,000 | 759 | 515 | 0 | 244 | 0.49% | 0.97x | +194.98% | 11.29% |
| $5,000 | 759 | 716 | 0 | 43 | 0.41% | 0.82x | +242.49% | 11.46% |

---

### 1:2000 Leverage Simulation Matrix

| Balance | Signals | Executed (Strict EA) | Rejected Margin | Rejected Min Lot Risk | Mean Actual Risk % | Mean Distortion | Net Return % | Max DD % |
|-------:|--------:|--------------------:|----------------:|----------------------:|-------------------:|----------------:|-------------:|---------:|
| $5 | 759 | 0 | 759 | 0 | 0.00% | 0.00x | 0.00% | 0.00% |
| $10 | 759 | 0 | 759 | 0 | 0.00% | 0.00x | 0.00% | 0.00% |
| $25 | 759 | 0 | 759 | 0 | 0.00% | 0.00x | 0.00% | 0.00% |
| $50 | 759 | 0 | 0 | 759 | 25.80% | 51.61x | 0.00% | 0.00% |
| $100 | 759 | 0 | 0 | 759 | 12.90% | 25.80x | 0.00% | 0.00% |
| $250 | 759 | 0 | 0 | 759 | 5.16% | 10.32x | 0.00% | 0.00% |
| **$500** | **759** | **0** | **0** | **759** | **2.58%** | **5.16x** | **0.00%** | **0.00%** |
| $1,000 | 759 | 50 | 0 | 709 | 1.29% | 2.58x | +11.20% | 4.10% |
| $1,500 | 759 | 173 | 0 | 586 | 0.87% | 1.73x | +45.80% | 6.20% |
| $2,000 | 759 | 330 | 0 | 429 | 0.66% | 1.32x | +112.40% | 8.50% |
| $2,500 | 759 | 438 | 0 | 321 | 0.55% | 1.09x | +165.20% | 9.80% |
| $3,000 | 759 | 515 | 0 | 244 | 0.49% | 0.97x | +194.98% | 11.29% |
| $5,000 | 759 | 716 | 0 | 43 | 0.41% | 0.82x | +242.49% | 11.46% |

---

## 4. Key Simulation Takeaways
1. **At $50 and $100**: Moving from 1:500 to 1:2000 eliminates margin rejections entirely (margin rejections drop from 758 to 0 at $50). However, trades transfer directly into `MIN_LOT_EXCEEDS_RISK` rejections.
2. **At $500**: Required margin is already easily satisfied at 1:500 ($8.70 < $500). Therefore, moving to 1:2000 produces **IDENTICAL** trade execution counts, risk percentages, and drawdown curves.
3. **Minimum Viable Balance**: To achieve genuine risk compliance ($\le 0.50\%$ risk per trade) on 100% of historical trades without relying on min-lot risk distortion, a balance of **$6,895** is required (for worst-case stop $34.48). For mean stop ($12.90), **$2,580** is required.

---

## 5. Final Simulation Conclusion
Leverage 1:2000 solves the **margin capacity problem** for accounts below $250. It does **NOT** solve the **minimum-lot risk distortion problem** for a $500 account at 0.5% risk.
