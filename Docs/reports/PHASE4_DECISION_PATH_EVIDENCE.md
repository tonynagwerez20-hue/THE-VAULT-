# PHASE 4 DECISION PATH EVIDENCE
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. End-to-End Decision Trace Proof

```text
[Stage 1: Market Observation]
  M5 Bar Close -> BuildMarketSnapshot(g_symbol, g_snap)
               │
               ▼
[Stage 2: Feature Vector Assembly]
  BuildFeatureVector(g_symbol, g_cfg, g_feat)
  - Proxy VWAP & ATR Deviation: Z_vwap = (Close - VWAP) / ATR
  - Activity Profile: POC, VAH (70%), VAL
  - Footprint Pressure: P_t = Σδ / (Σ|δ| + ε)
  - Structural Direction: -1 (Bearish) / 0 (Neutral) / +1 (Bullish)
               │
               ▼
[Stage 3: External Context Handoff]
  ReadExternalContext(g_cfg.bridge_inbox, g_ext, err)
  - Schema Version Check: 100
  - File Modify Age Check: <= 120s
  - CFTC COT Net Position & Extreme Flag
  - Options Proxy Basis & Gamma Regime
  - Reconciled News State
               │
               ▼
[Stage 4: Regime Engine Evaluation]
  EvaluateRegime(g_feat, g_cfg)
  - Evaluates scores for TREND_UP, TREND_DOWN, EXPANSION, BALANCED, EXHAUSTION
  - Applies 2-bar persistence & 0.10 hysteresis gates
               │
               ▼
[Stage 5: Strategy Engine Scoring]
  ScoreStrategies(g_feat, g_ext, g_cfg)
  - Continuation Evidence: s_long_cont, s_short_cont
  - Mean Reversion Evidence: s_long_mr, s_short_mr
  - CFTC Modifier (+-0.05) & Options Gamma Modifier (+-0.05)
               │
               ▼
[Stage 6: Decision Gate & Hard Risk Filter]
  Decide(ss, rs, g_ext, g_cfg, data_quality)
  - Veto on DQ_FATAL, DQ_MISSING_TICKS, DQ_BROKER_INVALID
  - Veto on REGIME_NO_TRADE
  - Filter on score_threshold (0.35) & margin (0.05)
  - RiskAllows(g_cfg, risk_reason) -> Hard 5.0% DD limit
               │
               ▼
[Stage 7: Shadow Telemetry Output]
  LogDecision(decision_id, g_symbol, dr.action, ...)
  LogFeatureDiagnostics(...)
  FlowShadowLogEntry.to_log_string() -> [FLOW_SHADOW] log
```

---

## 2. Decision Path Consumer Audit
- **Consumed & Active**: Proxy VWAP, POC/VAH/VAL, Footprint Pressure, CFTC Net Position, Options Basis, Reconciled News.
- **Shadow Logged (Disconnected from Trade Entry)**: Cumulative Delta (`m_cumulative_delta`), ATR Event Reaction (`EventReactionEngine`).
