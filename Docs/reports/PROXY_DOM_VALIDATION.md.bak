# PROXY DOM VALIDATION REPORT
**AlgoMind / ASAP Retail Order-Flow Project**

## 1. Concept & Integrity Standard
The AlgoMind Proxy DOM is an **Activity-at-Price Ladder**. It visually aggregates executed tick volume, estimated buy/sell distribution, and net delta across active price levels around current market price.

## 2. Distinction from Centralized Depth
- **No Liquidity Invention**: Resting limit order quantities are never fabricated.
- **Broker Depth (`MarketBookGet`)**: When provided by broker MT5 feeds, top-of-book depth is populated and tagged `BROKER-SUPPLIED DEPTH`.
- **Primary Function**: Provides visual and algorithmic context on price-level volume concentration without falsely claiming institutional order book visibility.
