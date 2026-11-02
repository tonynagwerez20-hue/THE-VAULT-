# DATA QUALITY AND PROVENANCE AUDIT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Provenance Tagging Audit

| Data Field / Feature | Raw Source | Quality Tag | Prohibition Rule | Status Label |
| :--- | :--- | :--- | :--- | :--- |
| **Retail Ticks / Spreads** | Broker MT5 Feed | `PROXY` / `ESTIMATED_DIRECTION` | Never call institutional order flow. | `IMPLEMENTED AND VERIFIED` |
| **Footprint Pressure** | Retail Tick Binning | `PROXY` | Never call centralized delta. | `IMPLEMENTED AND VERIFIED` |
| **Cumulative Delta** | Retail Bin Accumulator| `PROXY` | Never call institutional cumulative volume. | `IMPLEMENTED AND VERIFIED` |
| **Broker Market Depth** | MT5 `MarketBookGet` | `BROKER-SUPPLIED DEPTH` | Never call exchange level-2 DOM. | `IMPLEMENTED AND VERIFIED` |
| **Futures OHLCV** | AXB0306 CME Repo | `TRUE` (for OHLCV) | Tagged `footprint_available = false`. | `IMPLEMENTED AND VERIFIED` |
| **CFTC COT Report** | CFTC Disaggregated | `TRUE` | Strictly point-in-time (`available_from`). | `IMPLEMENTED AND VERIFIED` |
| **Proxy Options GLD** | CBOE / Yahoo Finance | `PROXY` / `ESTIMATED` | Never call total dealer positioning. | `IMPLEMENTED AND VERIFIED` |

---

## 2. Prohibition Audit
No retail proxy feature is permitted to upgrade its quality tag to `TRUE` without genuine exchange trade-side data.
