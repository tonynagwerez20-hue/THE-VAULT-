# PROXY FOOTPRINT SPECIFICATION
**AlgoMind / ASAP Retail Order-Flow System**

## 1. Architecture Migration
Migration from standalone proxy-delta dynamics to a **Footprint-First Architecture**:

```text
Market Ticks / Quotes
         │
         ▼
    Price Bins
         │
         ▼
  Proxy Footprint (Buy/Sell Activity Estimate)
         │
         ▼
    Proxy Delta
         │
         ▼
Cumulative Delta (CD)
         │
         ▼
Footprint Pressure / Events (Surge, Flip, Transition)
         │
         ▼
   Strategy Engine
```

## 2. Price Binning & Classification Rule
- Price bins are rounded using deterministic symbol tick boundaries ($0.01$ for XAUUSD):
  $$\text{Bin}(P) = \text{Round}\left(\frac{P}{\text{TickSize}}\right) \cdot \text{TickSize}$$
- Buy/sell allocation uses the Tick Rule estimator:
  - $P_t > P_{t-1} \rightarrow \text{ESTIMATED_BUY}$
  - $P_t < P_{t-1} \rightarrow \text{ESTIMATED_SELL}$
  - $P_t = P_{t-1} \rightarrow \text{CARRY_FORWARD_DIRECTION}$

## 3. Footprint Metrics
- **Activity per Bin**: $V(p) = V_{\text{buy}}(p) + V_{\text{sell}}(p)$
- **Bin Delta**: $\hat{\Delta}(p) = V_{\text{buy}}(p) - V_{\text{sell}}(p)$
- **Footprint Pressure**: $P_t = \frac{\sum \hat{\Delta}(p)}{\sum |\hat{\Delta}(p)| + \epsilon} \in [-1.0, +1.0]$
- **State Classification**: `BULLISH` ($P_t \ge +0.25$), `NEUTRAL` ($-0.25 < P_t < +0.25$), `BEARISH` ($P_t \le -0.25$).
