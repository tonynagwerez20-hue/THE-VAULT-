# DATA SOURCE AUDIT REPORT
**AlgoMind / ASAP Retail Order-Flow Project**
**Date:** September 23, 2026

## 1. Executive Summary
This document provides a factual audit of all available zero-cost reference and retail data sources evaluated for the AlgoMind Retail Order-Flow engine.

---

## 2. Source Inventory & Scorecard

| Source Name | Free | Historical | Live | Venue / Exchange | Data Type | Footprint Support | License / Access | Quality Tag |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MT5 Retail Feed** | Yes | Yes (Ticks) | Yes | Retail Broker (XAUUSD/XAUUSDm) | Ticks / Quotes | Estimated (Tick Rule) | Broker MT5 Account | `PROXY` |
| **AXB0306 CME Repo** | Yes | Yes (Daily) | No | CME / COMEX Gold (GC) | OHLCV | No (OHLCV only) | Free Public GitHub | `TRUE` (for OHLCV) |
| **Klustra / Hyperliquid**| Yes | Yes (Perp) | Yes | Hyperliquid DEX (GOLD-PERP) | L2 / Trade Feed | Yes (Decentralized) | Free Public API | `PROXY` |
| **Portara Samples** | Yes | Yes (Sample)| No | CME / COMEX Gold | Tick & Level 1 | Yes (Historical Sample)| Free Sample Download | `TRUE` |
| **MarketByOrder** | Yes | Replay | No | CME / COMEX | L2 / Depth | Yes (Replay mode) | Free Web Replay | `LIMITED` |
| **EV Trading Labs** | Yes | Yes (Sample)| No | Retail XAUUSD | Aggregated Activity | Estimated | Free Sample Download | `PROXY` |
| **FirstRateData** | Yes | Sample | No | Futures GC | Daily / Minute OHLC | No | Free Sample Download | `LIMITED` |
| **MarketParquet** | Yes | Sample | No | Futures GC | Parquet Sample | No | Free Sample Download | `LIMITED` |
| **Databento / Sierra**| **No** | N/A | N/A | CME / Paid Feeds | Paid Tick / MBO | N/A | `PAID — NOT USED` | `EXCLUDED` |

---

## 3. Data Provenance & Boundary Rules
1. **Exchange OHLCV (`TRUE`)**: Useful for reference VWAP and high-level regime context, but explicitly tagged `footprint_available = false` because OHLCV lacks sub-bar aggressor classification.
2. **MT5 Ticks (`PROXY`)**: Retail tick data provides timestamp, price, volume, bid, and ask. Buy/sell classification uses the **Tick Rule** ($P_t > P_{t-1} \rightarrow \text{BUY}$, $P_t < P_{t-1} \rightarrow \text{SELL}$).
3. **Crypto Gold Perps (`PROXY`)**: Hyperliquid `GOLD-PERP` serves as an independent order-flow benchmark. Note: `GOLD-PERP` $\neq$ COMEX GC $\neq$ Retail XAUUSD CFD.
