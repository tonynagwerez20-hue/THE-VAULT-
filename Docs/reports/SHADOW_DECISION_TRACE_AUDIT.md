# SHADOW DECISION TRACE AUDIT REPORT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Decision Trace Pipeline

```text
[1. Tick Arrival (M5 Bar Close)]
               │
               ▼
[2. Feature Snapshot Assembly (`BuildFeatureSnapshot`)]
               │
               ▼
[3. External Context Read (`ReadExternalContext` from `algomind_ext_in.txt`)]
               │
               ▼
[4. Regime Evaluation (`EvaluateRegime` in `Regime Engine.mqh`)]
               │
               ▼
[5. Strategy Scoring (`ScoreStrategies` in `Strategy Engine.mqh`)]
               │
               ▼
[6. Shadow Flow Log Generation (`FlowShadowLogEntry.to_log_string()`)]
               │
               ▼
[7. Decision Gate (`Decide` in `Strategy Engine.mqh`)]
               │
               ▼
[8. Hard Risk Check (`CheckRiskLimits` in `Risk Engine.mqh`)]
               │
               ▼
[9. Canonical Log Output (`LogMsg` / `[FLOW_SHADOW]`)]
```

---

## 2. Structured Log Entry Format Audit
Every shadow decision evaluates both live strategy scores and shadow flow metrics:

```text
[FLOW_SHADOW] ts=2026-09-23T22:30:00Z sym=XAUUSD fus=0.550 fp_press=0.580 c_state=BULLISH fp_state=BULLISH c_surge=1 fp_surge=1 fp_trans=NEUTRAL_TO_BULLISH fp_flip=NONE_0 p_vwap=2000.450 vwap_dev=0.650 poc=2000.500 vah=2001.100 val=1999.800 dom=PROXY dq=PROXY
```

---

## 3. Disconnected Feature Audit
- **Cumulative Delta (`m_cumulative_delta`)**: Accurately calculated in `AM_Footprint.mqh` and `proxy_footprint.py`, but logged for shadow evaluation; NOT currently wired into `Decide()` scoring to prevent un-validated strategy changes. Status: `IMPLEMENTED BUT NOT CONNECTED TO DECISION PATH`.
- **ATR Event Reaction (`EventReactionEngine`)**: Evaluated in Python research lab; NOT currently wired into MQL5 trade entry gates. Status: `IMPLEMENTED BUT NOT CONNECTED TO DECISION PATH`.
