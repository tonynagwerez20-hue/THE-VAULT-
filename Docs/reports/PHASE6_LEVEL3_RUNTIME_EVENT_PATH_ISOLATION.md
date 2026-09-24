# ALGOMIND PHASE 6 LEVEL 3 RUNTIME EVENT-PATH ISOLATION REPORT

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW ONLY (`InpShadowOnly = true`)  
**Report Date:** 2026-09-24  
**Authoritative Level 3 Status:** `LEVEL 3 — PARTIALLY VERIFIED`  
**Level 4 Live Trading:** `NOT AUTHORIZED`  
**Git Commit / Push:** `NOT APPROVED`

---

## 1. GOVERNANCE MANDATE COMPLIANCE

- Strategy logic modified: **NONE**
- Signal thresholds modified: **NONE**
- Risk limits modified: **NONE**
- `InpShadowOnly` modified: **NO** (`InpShadowOnly = true` strictly preserved)
- Live trading enabled: **NO**
- Safety gates disabled: **NO**
- Decision engine / order execution altered: **NO**
- Terminal restarted / EA reattached: **NO**
- Unverified runtime claims made: **NO**

---

## 2. A. RUNTIME ENVIRONMENT

| Parameter | Observed Value | Verification Source |
| :--- | :--- | :--- |
| **Terminal PID** | `7964` (`terminal64.exe`) | Windows Process Manager |
| **Attached EA** | `AMIGO` (`AMIGO.ex5`, 86,210 bytes) | MT5 Experts Log (`08:01:32.853`) |
| **Symbol** | `XAUUSD` | MT5 Experts Log |
| **Timeframe** | `M5` | MT5 Experts Log |
| **EA Compile Timestamp** | `2026.09.24 07:27:05 AM` | Binary File System Metadata |
| **EA Init Timestamp** | `2026.09.24 08:01:32.853 AM` | `20260924.log` Log Output |
| **Observation Start Time** | `2026.09.24 08:01:32.853 AM` | Log Window Start |
| **Observation End Time** | `2026.09.24 08:36:50.000 AM` | Current Live Inspection Time |

---

## 3. B. FRESH RUNTIME EVIDENCE

### 1. Initialization Evidence (08:01:32.853 AM) — VERIFIED RUNTIME:
```text
2026.09.24 08:00:15.043	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][DEINIT] reason=1
2026.09.24 08:01:32.853	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][INIT] AlgoMind started on XAUUSD tf=5 ML=OFF
2026.09.24 08:01:32.853	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK1] TICK_SZ=0.00100 TICK_VAL=0.10000 TICK_VAL_PROF=0.10000 TICK_VAL_LOSS=0.10000 CS=100.0 VOL_MIN=0.01 VOL_STEP=0.01 VOL_MAX=200.00 PT=0.00100 DIG=3
2026.09.24 08:01:32.853	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK2_BUY] 1.00lot(0.001=0.1000, 0.01=1.0000, 1.00=100.0000) | 0.10lot(0.001=0.0100, 0.01=0.1000, 1.00=10.0000) | 0.01lot(0.001=0.0000, 0.01=0.0100, 1.00=1.0000)
2026.09.24 08:01:32.853	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK2_SELL] 1.00lot(1.00=100.0000) | 0.10lot(1.00=10.0000) | 0.01lot(1.00=1.0000)
2026.09.24 08:01:32.853	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK4] stop=0.50 risk_b=2.50 raw=0.05000 norm=0.45 min_loss=0.50 ocp_min_loss=0.50 dec=APPROVED
...
2026.09.24 08:01:32.853	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK4] stop=5.00 risk_b=2.50 raw=0.00500 norm=0.04 min_loss=5.00 ocp_min_loss=5.00 dec=APPROVED
```

### 2. Post-Init Runtime Evidence (08:01:32 to 08:36:50 AM) — UNVERIFIED:
- **Observed Log Output:** 0 new lines emitted.
- **M5 Boundaries Passed in Observation Window:** 7 candle boundaries (`08:05`, `08:10`, `08:15`, `08:20`, `08:25`, `08:30`, `08:35`).
- **`FLOW_DIAG` Evidence:** 0 lines observed.
- **`DECISION` Evidence:** 0 lines observed.
- **`DIAG` Evidence:** 0 lines observed.
- **Error / Warning Evidence:** 0 error lines observed.

---

## 4. C. EVENT-PATH CLASSIFICATION

| Pipeline Stage | Status | Empirical / Analytical Grounding |
| :--- | :--- | :--- |
| **EA Initialization** | `VERIFIED RUNTIME` | `08:01:32.853` init log entries in active MT5 log stream matching post-07:27 binary. |
| **Tick Reception** | `UNVERIFIED` | Ticks are silent in `AMIGO.mq5`; no direct tick reception log exists post-init. |
| **`OnTick()` Execution** | `UNVERIFIED` | `OnTick()` contains no diagnostic log statements prior to new-bar branch. |
| **New-Bar Detection** | `UNVERIFIED` | `bar_time == g_last_bar_time` check outcome has not been logged. |
| **`OnClosedBar()` Execution** | `UNVERIFIED` | Function entry has not emitted any log line during observation window. |
| **Market Snapshot Build** | `UNVERIFIED` | `BuildMarketSnapshot()` execution result unconfirmed by log telemetry. |
| **Feature Vector Build** | `UNVERIFIED` | `BuildFeatureVector()` execution result unconfirmed by log telemetry. |
| **`FLOW_DIAG` Output** | `UNVERIFIED` | `FLOW_DIAG` format lines not observed in Experts log or disk file. |
| **Decision Pipeline** | `UNVERIFIED` | `Decide()` and `LogDecision()` output not observed in log stream. |
| **Shadow Interception** | `UNVERIFIED` | Interception block (`InpShadowOnly = true`) unreached without candidate trade. |
| **Failure Injection** | `UNVERIFIED` | Dynamic fault injection test pending confirmed runtime stream. |
| **Python ↔ MQL5 Live Parity**| `UNVERIFIED` | Live stream comparison pending confirmed MQL5 telemetry. |

---

## 5. D. DISK LOGGING ASSESSMENT

To preserve strict empirical standards, logging dynamics are categorized into four distinct categories:

- **OBSERVED:**
  - `20260924.log` LastWriteTime is `9/24/2026 8:02:20 AM`.
  - The file contains initialization entries at `08:01:32.853` and no subsequent entries up to `08:36:50`.
- **INFERRED:**
  - If `OnClosedBar()` had executed and completed normally, `FLOW_DIAG` and `LogDecision` would have passed string buffers to MT5's `PrintFormat()` routine.
- **HYPOTHESIZED (`CURRENT HYPOTHESIS — NOT VERIFIED`):**
  - Hypothesis A: MT5 log buffers `PrintFormat` output in RAM until a buffer size limit is reached or file handles are closed/flushed on deinit.
  - Hypothesis B: `OnTick()` is not being called by MT5 (e.g., chart ticker stalled, market quiet, or symbol session inactive).
  - Hypothesis C: `OnTick()` is called, but early-exits or fails silently (e.g. `iTime()` returning 0 or `BuildMarketSnapshot` returning false without error logging).
- **UNVERIFIED:**
  - Neither asynchronous buffer delay nor tick starvation is proven without targeted diagnostic instrumentation.

---

## 6. E. STATIC-VS-RUNTIME SEPARATION

| Information / Finding | Classification Source | Status |
| :--- | :--- | :--- |
| `AMIGO.mq5` calls `OnClosedBar()` inside `OnTick()` on bar change | `SOURCE INSPECTION` | `VERIFIED STATIC ONLY` |
| `AMIGO.mq5` logs `FLOW_DIAG` inside `OnClosedBar()` | `SOURCE INSPECTION` | `VERIFIED STATIC ONLY` |
| `InpShadowOnly = true` intercepts orders in `Execution Engine.mqh` | `SOURCE INSPECTION` | `VERIFIED STATIC ONLY` |
| MT5 process PID 7964 is active | `LIVE MT5 RUNTIME OBSERVATION` | `VERIFIED RUNTIME` |
| `AMIGO.ex5` initialized at `08:01:32.853` on `XAUUSD, M5` | `LIVE MT5 RUNTIME OBSERVATION` | `VERIFIED RUNTIME` |
| `OnClosedBar()` executed at M5 candle boundaries | `LIVE MT5 RUNTIME OBSERVATION` | `UNVERIFIED` |

---

## 7. F. MINIMAL DIAGNOSTIC INSTRUMENTATION PROPOSAL (SECTION 8 AUDIT)

Because post-reattachment runtime telemetry remains unobserved, we propose 5 minimal, non-strategy diagnostic points to isolate the exact step where execution stops or logs fail to emit:

### Diagnostic Point 1: `OnTick()` Entry Verification
- **File:** `MQL5/Experts/AMIGO.mq5`
- **Function:** `OnTick()`
- **Approximate Line:** L228
- **Current Statement:** `RiskTick();`
- **Proposed Diagnostic:**
  ```mql5
  static datetime s_last_tick_diag = 0;
  if(TimeCurrent() - s_last_tick_diag >= 60) {
     PrintFormat("[DIAG][ONTICK] tick_time=%s bid=%.5f ask=%.5f", TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS), SymbolInfoDouble(g_symbol, SYMBOL_BID), SymbolInfoDouble(g_symbol, SYMBOL_ASK));
     s_last_tick_diag = TimeCurrent();
  }
  ```
- **Why this proves the event:** Empirically proves whether MT5 invokes `OnTick()` and whether ticks arrive at the EA. Throttled to once every 60 seconds to prevent log spam.
- **Potential side effect:** Emits 1 line per minute.
- **Changes strategy behavior:** **NO**.

### Diagnostic Point 2: New-Bar Condition Evaluation
- **File:** `MQL5/Experts/AMIGO.mq5`
- **Function:** `OnTick()`
- **Approximate Line:** L263-265
- **Current Statement:**
  ```mql5
  datetime bar_time = iTime(g_symbol, g_cfg.tf_exec, 0);
  if(bar_time == g_last_bar_time) return;
  g_last_bar_time = bar_time;
  ```
- **Proposed Diagnostic:**
  ```mql5
  datetime bar_time = iTime(g_symbol, g_cfg.tf_exec, 0);
  if(bar_time != g_last_bar_time) {
     PrintFormat("[DIAG][BAR_CHANGE] prev_bar=%s new_bar=%s iTime_ok=%s", TimeToString(g_last_bar_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS), TimeToString(bar_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS), (bar_time > 0) ? "YES" : "NO");
  }
  if(bar_time == g_last_bar_time) return;
  g_last_bar_time = bar_time;
  ```
- **Why this proves the event:** Empirically proves whether `iTime()` succeeds and whether `bar_time` changes to trigger `OnClosedBar()`.
- **Potential side effect:** Emits 1 line per M5 bar change.
- **Changes strategy behavior:** **NO**.

### Diagnostic Point 3: `OnClosedBar()` Entry & Session Gate Audit
- **File:** `MQL5/Experts/AMIGO.mq5`
- **Function:** `OnClosedBar()`
- **Approximate Line:** L273-279
- **Current Statement:**
  ```mql5
  MqlDateTime dt;
  TimeToStruct(TimeCurrent(), dt);
  if(dt.hour < g_cfg.session_start_hour || dt.hour >= g_cfg.session_end_hour) return;
  ```
- **Proposed Diagnostic:**
  ```mql5
  MqlDateTime dt;
  TimeToStruct(TimeCurrent(), dt);
  PrintFormat("[DIAG][ONCLOSEDBAR_ENTER] time=%s hour=%d session_start=%d session_end=%d", TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS), dt.hour, g_cfg.session_start_hour, g_cfg.session_end_hour);
  ```
- **Why this proves the event:** Empirically proves `OnClosedBar()` is entered and whether the session hour gate blocks execution.
- **Potential side effect:** Emits 1 line per M5 bar change.
- **Changes strategy behavior:** **NO**.

### Diagnostic Point 4: `BuildMarketSnapshot()` Outcome Audit
- **File:** `MQL5/Experts/AMIGO.mq5`
- **Function:** `OnClosedBar()`
- **Approximate Line:** L282-286
- **Current Statement:**
  ```mql5
  if(!BuildMarketSnapshot(g_symbol, g_snap)) { LogMsg(LOG_WARN, "BAR", "snapshot build failed"); return; }
  ```
- **Proposed Diagnostic:**
  ```mql5
  bool snap_res = BuildMarketSnapshot(g_symbol, g_snap);
  PrintFormat("[DIAG][SNAPSHOT] result=%s bid=%.5f ask=%.5f atr14=%.5f dq=%d", snap_res ? "SUCCESS" : "FAILED", g_snap.bid, g_snap.ask, g_snap.atr14, g_snap.data_quality);
  if(!snap_res) return;
  ```
- **Why this proves the event:** Empirically proves whether market data/rates retrieval succeeds or fails.
- **Potential side effect:** Emits 1 line per M5 bar change.
- **Changes strategy behavior:** **NO**.

### Diagnostic Point 5: `BuildFeatureVector()` Outcome Audit
- **File:** `MQL5/Experts/AMIGO.mq5`
- **Function:** `OnClosedBar()`
- **Approximate Line:** L289-293
- **Current Statement:**
  ```mql5
  if(!BuildFeatureVector(g_symbol, g_cfg, g_feat)) { LogMsg(LOG_WARN, "BAR", "feature build failed"); return; }
  ```
- **Proposed Diagnostic:**
  ```mql5
  bool feat_res = BuildFeatureVector(g_symbol, g_cfg, g_feat);
  PrintFormat("[DIAG][FEATURES] result=%s timestamp=%s z_score=%.2f", feat_res ? "SUCCESS" : "FAILED", TimeToString(g_feat.timestamp, TIME_DATE|TIME_MINUTES|TIME_SECONDS), g_feat.z_score);
  if(!feat_res) return;
  ```
- **Why this proves the event:** Empirically proves whether feature vector compilation succeeds prior to `FLOW_DIAG` logging.
- **Potential side effect:** Emits 1 line per M5 bar change.
- **Changes strategy behavior:** **NO**.

---

## 8. G. NEXT GATE SELECTION

Selected Next Gate: **`B — Add minimal diagnostic instrumentation proposal`**

**Rationale:**  
The existing running EA has passed 7 M5 bar boundaries (`08:05` through `08:35`) without producing post-initialization log telemetry. Because strategy logic and risk limits are locked by governance, adding targeted, fail-safe diagnostic instrumentation (Points 1–5 above) is the only disciplined, evidence-based method to isolate the runtime event path.

---

## 9. FINAL GOVERNANCE STATUS

```text
LEVEL 3 — PARTIALLY VERIFIED

LEVEL 4 LIVE TRADING — NOT AUTHORIZED

GIT COMMIT — NOT APPROVED

GIT PUSH — NOT APPROVED
```
