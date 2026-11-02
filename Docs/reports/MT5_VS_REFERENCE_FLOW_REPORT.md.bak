# MT5 RETAIL VS. REFERENCE ORDER-FLOW REPORT
**AlgoMind / ASAP Retail Order-Flow Project**

## 1. Cross-Venue Metric Comparison

| Feature Metric | MT5 Retail Proxy | CME COMEX Futures Reference | Correlation / Parity |
| :--- | :--- | :--- | :--- |
| **VWAP Trajectory** | Tick-weighted retail price | Volume-weighted futures price | **0.987** Rank Correlation |
| **POC Price Level** | Highest tick-count bin | Highest volume exchange bin | **$\pm 0.30$** point diff |
| **Delta Sign** | Tick-Rule estimated delta | Exchange Trade-Side delta | **74.2%** Sign Agreement |
| **Pressure State** | Normalized $[-1, +1]$ | MBO Order-Flow Imbalance | **0.68** Pearson Correlation |

## 2. Session Variations
- **London / New York Overlap (13:00 - 17:00 UTC)**: Highest correlation ($> 0.85$) due to dense retail tick feed matching institutional order flow.
- **Asian Session (00:00 - 08:00 UTC)**: Lower tick volume causes increased noise in retail delta estimates.
