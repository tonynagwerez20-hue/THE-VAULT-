# UNRESOLVED OWNER DECISION REGISTER
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

## Decision Register Matrix

> [!IMPORTANT]
> The implementation agent operates under a strict no-invention policy. Items listed below represent technical choices that require explicit owner sign-off before being promoted to production rules.

| Decision ID | Area | Technical Choice / Alternatives | Default Research Baseline | Impact | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEC-001** | **Footprint Bin Size** | A) $0.01$ (Exact Tick)<br>B) $0.05$<br>C) $0.10$ | $0.01$ for XAUUSD | Price bin granularity in Python & MQL5 | `REQUIRES OWNER DECISION` |
| **DEC-002** | **Cumulative Delta Reset** | A) Daily / Session Open ($00:00$ UTC)<br>B) 50-Bar Rolling Window<br>C) Major News Event Reset | Session Reset ($00:00$ UTC) | CD baseline accumulation | `REQUIRES OWNER DECISION` |
| **DEC-003** | **News Reaction Window** | A) 15-Minute Pre/Post Window<br>B) 30-Minute Window<br>C) Dynamic Volatility-Based Window | 15-Minute Pre / 30-Minute Post | Blackout duration & event reaction scoring | `REQUIRES OWNER DECISION` |
| **DEC-004** | **Legacy Delta Retirement** | A) Retire legacy Proxy A/B/C delta immediately.<br>B) Maintain shadow dual-tracking until ablation report.<br>C) Blend 50/50. | Shadow Dual-Tracking | Strategy scoring transition | `REQUIRES OWNER DECISION` |
| **DEC-005** | **Cumulative Delta Integration**| A) Keep Cumulative Delta in shadow mode.<br>B) Connect Cumulative Delta divergence to Mean Reversion scoring gate. | Shadow Mode Only | Live strategy signal generation | `REQUIRES OWNER DECISION` |
| **DEC-006** | **Micro-Account Minimum Vol Risk**| A) Reject trade if min volume ($0.01$) exceeds allowed risk % (`NO_TRADE`).<br>B) Execute min volume anyway.<br>C) Scale stop distance. | Reject (`NO_TRADE`) | Micro-account trade frequency | `REQUIRES OWNER DECISION` |
| **DEC-007** | **Live Promotion Authorization**| A) Authorize live trial execution.<br>B) Maintain Shadow Mode indefinitely until OOS walk-forward validation. | Shadow Mode Indefinitely | Live trade order submission | `REQUIRES OWNER DECISION` |
