# AMIGO — Timeframe Authority and Alignment Matrix

## 1. Timeframe Authority Hierarchy

The analytical model organizes timeframes by structural authority:

| Scale Tier | Timeframes | Authority Weight | Governing Responsibility | Conflict Resolution Rule |
| :--- | :--- | :--- | :--- | :--- |
| **HTF Macro** | D1, H4 | **50%** | Directional regime, major market structure, key daily swing levels | **Overrides** lower timeframe trend assumptions. |
| **Intermediate** | H1, M30 | **30%** | Trend maturity, value migration, pullback validation | Validates continuation health. |
| **LTF Execution**| M15, M5, M1 | **20%** | Entry trigger, local invalidation, micro footprint pressure | Subordinate to HTF; provides execution timing. |

---

## 2. Multi-Timeframe Alignment States & Operational Directives

| D1 / H4 Bias | H1 / M30 Bias | M15 / M5 Bias | Alignment Classification | Operational Directive | Permitted Horizons | Eligible Hypothesis |
| :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **Bullish (+1)** | **Bullish (+1)** | **Bullish (+1)** | **FULL_ALIGNMENT_BULL** | Aggressive trend continuation on pullbacks. Full risk budget. | Scalp, Intraday, Swing | `HYP_CONTINUATION` |
| **Bearish (-1)** | **Bearish (-1)** | **Bearish (-1)** | **FULL_ALIGNMENT_BEAR** | Aggressive trend continuation on rallies. Full risk budget. | Scalp, Intraday, Swing | `HYP_CONTINUATION` |
| **Bullish (+1)** | **Bullish (+1)** | **Bearish (-1)** | **PULLBACK_INTO_SUPPORT** | Await local exhaustion; enter Long on micro CHoCH flip. | Scalp, Intraday | `HYP_CONTINUATION` (on turn) |
| **Bearish (-1)** | **Bearish (-1)** | **Bullish (+1)** | **PULLBACK_INTO_RESISTANCE**| Await local exhaustion; enter Short on micro CHoCH flip. | Scalp, Intraday | `HYP_CONTINUATION` (on turn) |
| **Bullish (+1)** | **Bearish (-1)** | **Bearish (-1)** | **INTERMEDIATE_DIVERGENCE** | Trend weakening. Require structural reclamation before Long. | Intraday (Reduced Risk) | `HYP_CONTINUATION` |
| **Bearish (-1)** | **Bullish (+1)** | **Bullish (+1)** | **INTERMEDIATE_DIVERGENCE** | Trend weakening. Require structural rejection before Short. | Intraday (Reduced Risk) | `HYP_CONTINUATION` |
| **Bullish (+1)** | **Neutral (0)** | **Bearish (-1)** | **HTF_LTF_CONFLICT** | High whipsaw risk. Shift to `REGIME_BALANCED`. | Scalp Only | `HYP_MEAN_REVERSION` (Strict) |
| **Bearish (-1)** | **Neutral (0)** | **Bullish (+1)** | **HTF_LTF_CONFLICT** | High whipsaw risk. Shift to `REGIME_BALANCED`. | Scalp Only | `HYP_MEAN_REVERSION` (Strict) |
| **Any** | **Any** | **Any (Stale)** | **DATA_QUALITY_DEGRADED** | Timeframe bars stale or missing. Immediate `ACTION_NO_TRADE`. | None | None |

---

## 3. Strict Rules for Countertrend Mean Reversion

A countertrend trade (e.g. attempting to Buy when H4/D1 is Bearish) is prohibited under standard trend regimes. It is permitted **strictly and only if all of the following conditions are simultaneously met**:

1. **Macro Extension**: Current price is deviated by $\ge 2.0 \times \text{ATR}_{14}$ from Session VWAP or higher-timeframe Value Area High/Low.
2. **Confirmed Liquidity Sweep & Rejection**:
   - `f.sweep_reject == true` (Price swept recent swing extreme and snapped back inside range).
   - In M5/M15 rates, `IsConfirmedSwingLow` or `IsConfirmedSwingHigh` is formed.
3. **Orderflow Delta Exhaustion**:
   - Extreme cumulative delta with zero follow-through (absorption).
4. **Target Feasibility & Mandatory R:R**:
   - The reversion target (Session VWAP or POC) must offer at least **2.0 R:R** relative to the structural invalidation level.
5. **Reduced Exposure Policy**:
   - Maximum risk is throttled to 50% of base risk budget (`risk_modifier = 0.50`).
