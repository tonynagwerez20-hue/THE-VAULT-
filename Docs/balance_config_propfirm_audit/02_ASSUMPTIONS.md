# 02 — AUDIT & MODEL ASSUMPTIONS

## 1. Symbol Specifications (XAUUSDm)
- **Contract Size**: 100 troy ounces per 1.0 lot.
- **Tick Size**: 0.01 price unit ($0.01).
- **Tick Value**: $1.00 per 1.0 lot ($0.01 per 0.01 lot per $0.01 price move).
- **Minimum Volume**: 0.01 lot.
- **Volume Step**: 0.01 lot.
- **Account Base Currency**: USD.
- **Leverage**: 1:100 standard.
- **Margin Required**: ~$38.70 per 0.01 lot at ~$3,870 gold price.

## 2. Viability Criteria Definitions
- **Technical Floor**: Minimum balance required to open 0.01 lot margin ($50).
- **Conservative Viability Regime**:
  - Minimum-Lot Risk Distortion $\le 1.25$ ($\le 25\%$ average excess risk).
  - Setup Executability $\ge 95.0\%$.
  - Maximum Historical Drawdown $\le 15.0\%$.
- **Aggressive Viability Regime**:
  - Minimum-Lot Risk Distortion $\le 2.50$ ($\le 150\%$ average excess risk).
  - Setup Executability $\ge 75.0\%$.
  - Maximum Historical Drawdown $\le 35.0\%$.
