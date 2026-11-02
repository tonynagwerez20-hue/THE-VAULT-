# ALGOMIND PHASE 6 — GATE B DIAGNOSTIC INSTRUMENTATION PLAN

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Target File:** `MQL5/Experts/AMIGO.mq5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW ONLY (`InpShadowOnly = true`)  
**Document Status:** `READY FOR REVIEW` (Code changes NOT yet applied)  
**Authoritative Level 3 Status:** `LEVEL 3 — PARTIALLY VERIFIED`  
**Level 4 Live Trading:** `NOT AUTHORIZED`  
**Git Commit / Push:** `NOT APPROVED`

---

## 1. PURPOSE AND OBJECTIVE

The purpose of this plan is to define the exact, minimal diagnostic instrumentation points required to isolate and verify the MT5 runtime event chain:

```text
MT5 Tick Arrival
       ↓
[DIAG][TICK_HEARTBEAT]
       ↓
OnTick()
       ↓
[DIAG][NEW_BAR_DETECTED]
       ↓
OnClosedBar()
       ↓
[DIAG][ONCLOSEDBAR_ENTRY]
       ↓
[DIAG][SNAPSHOT_RESULT] (BuildMarketSnapshot)
       ↓
[DIAG][FEATURE_RESULT]  (BuildFeatureVector)
       ↓
FLOW_DIAG Engine Telemetry
       ↓
DECISION Pipeline Output
```

This plan is **diagnostic-only**. It does not alter strategy calculations, signal generation, risk parameters, order execution, or shadow interception logic.

---

## 2. GOVERNANCE AND SAFETY AUDIT

| Constraint | Status | Audit Confirmation |
| :--- | :--- | :--- |
| **Strategy Logic Modified** | **NO** | No scoring, regime, or entry/exit rules modified. |
| **Risk Parameters Modified** | **NO** | `RiskEngine` inputs and calculations untouched. |
| **Execution Logic Modified** | **NO** | `Execution Engine` and order routines untouched. |
| **`InpShadowOnly` Preserved** | **YES** | `InpShadowOnly = true` remains strictly active. |
| **Compilation Performed** | **NO** | Code edit and compilation pending user review. |
| **MT5 Process Restarted** | **NO** | MT5 PID 7964 running continuously. |
| **Non-blocking / Fail-safe** | **YES** | No loops, sleeps, DLL calls, or blocking I/O added. |

---

## 3. PROPOSED INSTRUMENTATION POINTS

### Point 1: `OnTick()` Heartbeat Diagnostic
- **Target File:** `MQL5/Experts/AMIGO.mq5`
- **Target Function:** `OnTick()`
- **Approximate Line:** L228 (top of `OnTick()`)
- **Throttling Mechanism:** Throttled to execute at most once every 60 seconds of server time using a static timer variable (`s_last_tick_diag`).
- **Proposed MQL5 Code Snippet:**
  ```mql5
  //--- Diagnostic Point 1: Throttled OnTick Heartbeat (every 60 seconds)
  static datetime s_last_tick_diag = 0;
  if(TimeCurrent() - s_last_tick_diag >= 60)
  {
     double cur_bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
     double cur_ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
     datetime cur_bar = iTime(g_symbol, g_cfg.tf_exec, 0);
     PrintFormat("[DIAG][TICK_HEARTBEAT] server_time=%s sym=%s bid=%.5f ask=%.5f cur_bar=%s last_bar=%s",
                 TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                 g_symbol, cur_bid, cur_ask,
                 TimeToString(cur_bar, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                 TimeToString(g_last_bar_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS));
     s_last_tick_diag = TimeCurrent();
  }
  ```
- **Expected Diagnostic Output:**
  `[DIAG][TICK_HEARTBEAT] server_time=2026.09.24 08:45:12 sym=XAUUSD bid=2650.123 ask=2650.345 cur_bar=2026.09.24 08:45 last_bar=2026.09.24 08:40`
- **Proof Provided:** Empirically proves MT5 is actively invoking `OnTick()` on chart price movement and feeding current prices and bar timestamps to `AMIGO.mq5`.

---

### Point 2: New-Bar Detection Diagnostic
- **Target File:** `MQL5/Experts/AMIGO.mq5`
- **Target Function:** `OnTick()`
- **Approximate Line:** L263–L265
- **Location:** Immediately before the `if(bar_time == g_last_bar_time) return;` return gate.
- **Proposed MQL5 Code Snippet:**
  ```mql5
  //--- Decision only on new closed bar
  datetime bar_time = iTime(g_symbol, g_cfg.tf_exec, 0);
  if(bar_time != g_last_bar_time)
  {
     PrintFormat("[DIAG][NEW_BAR_DETECTED] server_time=%s bar_time=%s prev_last_bar=%s iTime_ok=%s",
                 TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                 TimeToString(bar_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                 TimeToString(g_last_bar_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                 (bar_time > 0) ? "YES" : "NO");
  }
  if(bar_time == g_last_bar_time) return;
  g_last_bar_time = bar_time;
  ```
- **Expected Diagnostic Output:**
  `[DIAG][NEW_BAR_DETECTED] server_time=2026.09.24 08:45:00 bar_time=2026.09.24 08:45 prev_last_bar=2026.09.24 08:40 iTime_ok=YES`
- **Proof Provided:** Empirically proves `iTime()` successfully evaluated a new M5 candle timestamp, passed the inequality test, updated `g_last_bar_time`, and proceeded to call `OnClosedBar()`.

---

### Point 3: `OnClosedBar()` Entry & Session Gate Diagnostic
- **Target File:** `MQL5/Experts/AMIGO.mq5`
- **Target Function:** `OnClosedBar()`
- **Approximate Line:** L272 (beginning of `OnClosedBar()`)
- **Location:** Top of `OnClosedBar()`, prior to session hour check.
- **Identification of Early Return Gates:**
  1. *Gate 0 (Session Hours):* `if(dt.hour < g_cfg.session_start_hour || dt.hour >= g_cfg.session_end_hour) return;`
  2. *Gate 1 (Market Snapshot):* `if(!BuildMarketSnapshot(g_symbol, g_snap)) return;`
  3. *Gate 2 (Feature Vector):* `if(!BuildFeatureVector(g_symbol, g_cfg, g_feat)) return;`
  4. *Gate 3 (ML Veto):* `if(ml.available && !ml.pass) return;`
- **Proposed MQL5 Code Snippet:**
  ```mql5
  void OnClosedBar()
  {
     //--- Diagnostic Point 3: OnClosedBar Entry & Session Audit
     MqlDateTime dt;
     TimeToStruct(TimeCurrent(), dt);
     bool session_pass = (dt.hour >= g_cfg.session_start_hour && dt.hour < g_cfg.session_end_hour);
     PrintFormat("[DIAG][ONCLOSEDBAR_ENTRY] server_time=%s sym=%s tf=%d closed_bar=%s hour=%d session=[%d-%d] pass=%s",
                 TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                 g_symbol, (int)g_cfg.tf_exec,
                 TimeToString(iTime(g_symbol, g_cfg.tf_exec, 0), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                 dt.hour, g_cfg.session_start_hour, g_cfg.session_end_hour,
                 session_pass ? "YES" : "NO");

     //--- 0) Session hour gate
     if(dt.hour < g_cfg.session_start_hour || dt.hour >= g_cfg.session_end_hour)
     {
        return;
     }
  ```
- **Expected Diagnostic Output:**
  `[DIAG][ONCLOSEDBAR_ENTRY] server_time=2026.09.24 08:45:00 sym=XAUUSD tf=5 closed_bar=2026.09.24 08:45 hour=8 session=[0-24] pass=YES`
- **Proof Provided:** Empirically proves `OnClosedBar()` was entered and evaluates whether Gate 0 (session hours) allowed continuation.

---

### Point 4: Market Snapshot Result Diagnostic
- **Target File:** `MQL5/Experts/AMIGO.mq5`
- **Target Function:** `OnClosedBar()`
- **Approximate Line:** L282–L286
- **Location:** Immediately following `BuildMarketSnapshot(g_symbol, g_snap)` call.
- **Proposed MQL5 Code Snippet:**
  ```mql5
  //--- 1) Snapshot
  bool snap_res = BuildMarketSnapshot(g_symbol, g_snap);
  PrintFormat("[DIAG][SNAPSHOT_RESULT] server_time=%s success=%s bid=%.5f ask=%.5f atr14=%.5f dq=%d",
              TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
              snap_res ? "YES" : "NO", g_snap.bid, g_snap.ask, g_snap.atr14, g_snap.data_quality);
  if(!snap_res)
  {
     LogMsg(LOG_WARN, "BAR", "snapshot build failed");
     return;
  }
  ```
- **Expected Diagnostic Output:**
  `[DIAG][SNAPSHOT_RESULT] server_time=2026.09.24 08:45:00 success=YES bid=2650.123 ask=2650.345 atr14=1.23450 dq=0`
- **Proof Provided:** Empirically proves whether `BuildMarketSnapshot()` succeeded or failed (Gate 1).

---

### Point 5: Feature Vector Result Diagnostic
- **Target File:** `MQL5/Experts/AMIGO.mq5`
- **Target Function:** `OnClosedBar()`
- **Approximate Line:** L289–L293
- **Location:** Immediately following `BuildFeatureVector(g_symbol, g_cfg, g_feat)` call.
- **Proposed MQL5 Code Snippet:**
  ```mql5
  //--- 2) Features
  bool feat_res = BuildFeatureVector(g_symbol, g_cfg, g_feat);
  PrintFormat("[DIAG][FEATURE_RESULT] server_time=%s success=%s ts=%s z_score=%.2f dq=%d",
              TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
              feat_res ? "YES" : "NO",
              TimeToString(g_feat.timestamp, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
              g_feat.z_score, g_feat.data_quality);
  if(!feat_res)
  {
     LogMsg(LOG_WARN, "BAR", "feature build failed");
     return;
  }
  ```
- **Expected Diagnostic Output:**
  `[DIAG][FEATURE_RESULT] server_time=2026.09.24 08:45:00 success=YES ts=2026.09.24 08:45 z_score=0.15 dq=0`
- **Proof Provided:** Empirically proves whether `BuildFeatureVector()` succeeded or failed (Gate 2) immediately prior to `FLOW_DIAG` logging.

---

## 4. POSSIBLE SIDE EFFECTS AND SAFETY ASSESSMENT

1. **CPU / Memory Impact:** Negligible. Throttled heartbeat executes 1 check per tick and logs once per 60 seconds. Points 2–5 execute at most once per 5-minute bar closure.
2. **Log Volume:** Adds ~1 log line per minute for heartbeat and ~4 log lines per M5 candle closure (~49 lines per hour).
3. **Execution Safety:** No loops, sleeps, blocking file operations, or external network/IPC calls. All calls use standard native `PrintFormat()`.
4. **Strategy Impact:** Zero logic modification. Variable assignments and logic gates remain identical to the uninstrumented source.

---

## 5. ROLLBACK AND REMOVAL PROCEDURE

If rollback is required:
1. Revert `MQL5/Experts/AMIGO.mq5` to its exact pre-instrumentation git state (`git checkout MQL5/Experts/AMIGO.mq5`).
2. Recompile `AMIGO.mq5` using `metaeditor64.exe /compile:MQL5\Experts\AMIGO.mq5`.
3. Overwrite `AMIGO.ex5` in the MT5 Experts directory (`D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\AMIGO.ex5`).

---

## 6. FINAL CLASSIFICATION BLOCK

```text
Instrumentation Plan: READY FOR REVIEW
Strategy Logic Modified: NO
Risk Logic Modified: NO
Execution Logic Modified: NO
Compilation Performed: NO
MT5 Restarted: NO
Commit: NOT APPROVED
Push: NOT APPROVED
```
