# REVERSE ENGINEERING STATUS

## TickMind AI (tickmindai.com)

### Publicly Observable Features
- Order-flow gold & forex signals
- Order-flow tools that read charts
- Login/account creation system
- Password recovery

### Data Source Assessment
- No public documentation of data sources
- No public API or technical specification
- Commercial service (login required for full features)
- Cannot determine whether exchange bid/ask, broker tick, or derived data is used
- **Limitation**: Full feature set is behind authentication — only landing page publicly observable

### Clean-Room Implementation Design
For AMIGO, the equivalent functionality would be:
- Proxy delta from MT5 tick data (already implemented in AMIGO_BASELINE)
- Footprint approximation from M1 bar volume
- VWAP from session ticks
- Volume profile from M1 bars
- All labeled as proxy data, not exchange data (per P-05)

### Status: RESEARCH COMPLETE (limited by public observability)

## NoLimitzBots (nolimitzbots.co.ke)

### Publicly Observable Features
- MT5 trading automation platform
- Five automation methods: AI Trader, Telegram Copier, TradingView Copier, Copy Trading, EA Automation
- AI Trader: Six agents (SCOUT, CHECK, SIZE, ENTRY, EXIT, GUARD) for gold trading
- Telegram Copier: Signal channel copying with shadow mode
- TradingView Copier: Webhook-based alert copying
- Copy Trading: Provider trade copying
- EA Automation: Cloud-hosted EA execution
- Risk controls: user-defined lot size and risk mode
- Shadow mode for testing
- Activity logging
- Works in phone browser, no VPS needed
- Funds stay at broker

### Top-Down Analysis Features (publicly observable)
- No explicit top-down analysis methodology described on public pages
- AI Trader mentions "find, size, enter, manage and protect" — implies multi-step analysis
- No mention of market structure, supply/demand, liquidity sweeps, premium/discount
- **Limitation**: Detailed analytical methodology is not publicly documented

### Clean-Room Implementation Design
AMIGO already implements:
- Multi-timeframe analysis (M1, M5, M15, H1, H4)
- Regime classification (trend up/down, balanced)
- Strategy evaluation (trend + mean reversion)
- Risk management with fail-closed behavior
- Trade arbitration

### Status: RESEARCH COMPLETE (limited by public observability)

## Comparative Evaluation
| Dimension | TickMind AI | NoLimitzBots | AMIGO Equivalent |
|-----------|-------------|--------------|------------------|
| Order flow | Claimed (proxy unknown) | Not claimed | Proxy delta (labeled) |
| Multi-TF analysis | Unknown | Claimed (AI agents) | Implemented (M1-H4) |
| Risk management | Unknown | User-configured | Fail-closed, MVE-verified |
| Execution | Unknown | Cloud-hosted EA | Native MQL5 |
| Data quality | Unknown | Unknown | MT5 broker ticks (labeled) |
| Verifiability | Low (closed) | Low (closed) | High (open source, auditable) |

## Conclusion
Neither product provides sufficient public documentation to reverse-engineer their internal algorithms. AMIGO's existing implementation is more transparent and auditable. Feature comparison is limited to publicly observable marketing claims. No proprietary code or confidential implementation was copied.