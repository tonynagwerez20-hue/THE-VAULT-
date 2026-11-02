# PROXY DELTA & CUMULATIVE DELTA SPECIFICATION
**AlgoMind / ASAP Retail Order-Flow System**

## 1. Derived Delta Formulation
Delta is derived directly from price-level footprint bins:

$$\hat{\Delta}_t = \sum_{p} \hat{\Delta}(p) = \sum_{p} \left( V_{\text{buy}}(p) - V_{\text{sell}}(p) \right)$$

## 2. Cumulative Delta (CD) Formulation & Reset Scopes
Cumulative Delta aggregates interval delta across defined session windows:

$$\text{CD}_t = \text{CD}_{t-1} + \hat{\Delta}_t$$

### Reset Policy Options:
1. **Session Reset (`SESSION`)**: Reset $\text{CD} = 0$ at Asian session open ($00:00$ UTC). Default proposed baseline.
2. **Rolling Window (`ROLLING_50`)**: Rolling sum of delta over the last 50 bars.
3. **Event Reset (`EVENT`)**: Reset $\text{CD} = 0$ at major economic news release timestamps.

## 3. Cumulative Delta Features
- `CD_change`: $\text{CD}_t - \text{CD}_{t-1}$
- `CD_slope`: Linear regression slope of CD over 5 bars.
- `CD_high` / `CD_low`: Session high and low bounds of Cumulative Delta.
- `price_vs_CD_divergence`:
  - `BULLISH_DIVERGENCE`: Price makes lower low while CD makes higher low.
  - `BEARISH_DIVERGENCE`: Price makes higher high while CD makes lower high.

## 4. Migration Governance
Legacy delta (`delta_A`, `delta_B`, `fusion`) runs in parallel with footprint-derived delta (`footprint_delta`, `cumulative_delta`) in **Shadow Mode**. Legacy delta will only be retired after explicit owner authorization.
