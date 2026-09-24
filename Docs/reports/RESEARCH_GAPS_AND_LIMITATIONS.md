# RESEARCH GAPS & LIMITATIONS AUDIT
**AlgoMind / ASAP Retail Order-Flow Project**

## 1. Strict Boundary Audit

1. **Retail Tick Direction vs. Aggressor Trade Side**:
   - MT5 tick feeds do not provide true aggressive buyer/seller flags. Direction is estimated via the **Tick Rule** ($P_t > P_{t-1}$).
   - Classification is tagged `PROXY` / `ESTIMATED_DIRECTION`.

2. **OHLCV Data Limitation**:
   - Free exchange datasets (e.g. CME OHLCV repo) provide TRUE OHLCV but CANNOT generate price-level footprint metrics.

3. **Retail Depth vs. Centralized DOM**:
   - Broker `MarketBookGet` depth reflects broker liquidity pools, NOT CME COMEX centralized depth.
   - Tagged `BROKER-SUPPLIED DEPTH`.

4. **Zero Lookahead Enforced**:
   - All feature calculations use strictly historical data up to time $t$.
