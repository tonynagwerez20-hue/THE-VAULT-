# ALGOMIND — FINAL BALANCE & PROP-FIRM VERDICT

## Technical Floor
$50

## Smallest Aggressive Viable Balance
$1,500

## Smallest Conservative Viable Balance
$3,000

## Balance Where Minimum-Lot Distortion Becomes Acceptable
$3,000

## Balance Where >=95% of Valid Historical Setups Are Executable
$50

## Conservative Configuration
- **Account Balance**: $3,000
- **Risk Per Trade**: 0.50% ($15.00 reference risk budget)
- **Max Historical Drawdown**: 11.09% (Balance DD) / 17.38% (MT5 Peak-to-Trough)
- **Profit Factor**: 1.80
- **Executability**: 100.0%
- **Average Risk Distortion**: 0.97 (Actual Risk 0.486%)

## Aggressive Configuration
- **Account Balance**: $1,500
- **Risk Per Trade**: 0.50% ($7.50 reference risk budget)
- **Max Historical Drawdown**: 22.98%
- **Profit Factor**: 1.80
- **Executability**: 100.0%
- **Average Risk Distortion**: 1.73 (Actual Risk 0.866%)

## FundedNext
- **Model**: Stellar 2-Step (50k Account)
- **Result**: **PASS** (at 0.20% Risk / Trade) | **FAIL** (at 0.50% Risk / Trade due to Daily Loss Breach)

## FundingPips
- **Model**: 2-Step Standard (50k Account)
- **Result**: **PASS** (at 0.20% Risk / Trade) | **FAIL** (at 0.50% Risk / Trade)

---

# EXECUTIVE EVIDENCE SUMMARY

1. **Minimum-Lot Distortion Audit**: On account balances below $3,000, the MT5 0.01 lot minimum volume constraint creates severe risk distortion. At $100, the average trade risks 12.90% instead of 0.50% (25.8x intended risk), causing rapid account ruin. At $3,000, average risk distortion drops to 0.97x, making $3,000 the strict mathematical conservative floor.
2. **Prop-Firm Optimization**: AlgoMind's baseline 0.50% risk configuration fails prop-firm challenge phases because its worst daily closed drawdown reaches 8.49% ($4,243.83 on $50k), violating the 5% ($2,500) daily loss ceiling. Reducing risk to **0.20% per trade** allows full compliance across FundedNext Stellar 2-Step and FundingPips 2-Step models with zero breaches.
