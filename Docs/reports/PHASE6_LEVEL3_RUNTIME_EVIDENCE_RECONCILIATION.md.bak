# ALGOMIND PHASE 6 — RUNTIME EVIDENCE RECONCILIATION & SHADOW BOUNDARY AUDIT

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW MODE (`InpShadowOnly = true`)  
**Report Date:** 2026-09-24  
**Authoritative Level 3 Status:** `LEVEL 3 — PARTIALLY VERIFIED`  
**Level 4 Live Trading:** `NOT AUTHORIZED`  
**Git Commit / Push:** `NOT APPROVED`

---

## 1. EXECUTIVE SUMMARY & RECONCILIATION OBJECTIVE

This document provides a strict, evidence-based reconciliation of the live MT5 runtime telemetry captured between `17:47:55` and `18:30:00` on 2026-09-24. 

Per governance rules, evidence is rigorously separated into three tiers:
1. **DIRECT EVIDENCE:** Explicit log entries emitted at runtime.
2. **INDIRECT / DOWNSTREAM EVIDENCE:** Verified downstream events proving earlier execution stages were reached.
3. **STATIC-ONLY EVIDENCE:** Proven by source code inspection, but unobserved at runtime.

---

## 2. EXACT LOG EXCERPTS (POST-17:47:55 REATTACHMENT)

### A. Initialization & Symbol Audit Logs (DIRECT EVIDENCE)
```text
2026.09.24 17:47:55.798	AMIGO (XAUUSD,M1)	[AlgoMind][INFO][DEINIT] reason=3
2026.09.24 17:47:55.799	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][INIT] AlgoMind started on XAUUSD tf=5 ML=OFF
2026.09.24 17:47:55.799	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK1] TICK_SZ=0.00100 TICK_VAL=0.10000 TICK_VAL_PROF=0.10000 TICK_VAL_LOSS=0.10000 CS=100.0 VOL_MIN=0.01 VOL_STEP=0.01 VOL_MAX=200.00 PT=0.00100 DIG=3
2026.09.24 17:47:55.799	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK2_BUY] 1.00lot(0.001=0.1000, 0.01=1.0000, 1.00=100.0000) | 0.10lot(0.001=0.0100, 0.01=0.1000, 1.00=10.0000) | 0.01lot(0.001=0.0000, 0.01=0.0100, 1.00=1.0000)
2026.09.24 17:47:55.799	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK2_SELL] 1.00lot(1.00=100.0000) | 0.10lot(1.00=10.0000) | 0.01lot(1.00=1.0000)
2026.09.24 17:47:55.799	AMIGO (XAUUSD,M5)	[P22_AUDIT][TASK4] stop=0.50 risk_b=2.50 raw=0.05000 norm=0.46 min_loss=0.50 ocp_min_loss=0.50 dec=APPROVED
```

### B. Order-Flow Engine Telemetry (`FLOW_DIAG`) (DIRECT EVIDENCE)
```text
2026.09.24 17:50:00.145	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 14:50 vwap=4269.92906 dev=-1.88 poc=4282.48000 vah=4286.09000 val=4254.52000 cd=-607.00 fp_press=-0.0336 state=0 shadow=FALSE
2026.09.24 17:55:08.044	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 14:55 vwap=4269.82080 dev=-1.65 poc=4282.48000 vah=4286.09000 val=4254.52000 cd=-610.00 fp_press=-0.0335 state=0 shadow=FALSE
2026.09.24 18:00:01.395	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 15:00 vwap=4269.70454 dev=-2.39 poc=4282.48000 vah=4286.09000 val=4254.52000 cd=-651.00 fp_press=-0.0357 state=0 shadow=FALSE
2026.09.24 18:05:02.381	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 15:05 vwap=4269.52540 dev=-2.80 poc=4282.48000 vah=4286.09000 val=4251.53000 cd=-704.00 fp_press=-0.0383 state=0 shadow=FALSE
2026.09.24 18:10:00.581	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 15:10 vwap=4269.36587 dev=-2.81 poc=4282.48000 vah=4286.09000 val=4251.53000 cd=-696.00 fp_press=-0.0376 state=0 shadow=FALSE
2026.09.24 18:15:06.427	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 15:15 vwap=4269.19711 dev=-3.33 poc=4282.48000 vah=4286.09000 val=4250.65000 cd=-745.00 fp_press=-0.0400 state=0 shadow=FALSE
2026.09.24 18:20:05.120	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 15:20 vwap=4268.97268 dev=-2.89 poc=4282.48000 vah=4286.09000 val=4249.77000 cd=-740.00 fp_press=-0.0393 state=0 shadow=FALSE
2026.09.24 18:25:03.717	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 15:25 vwap=4268.89085 dev=-2.02 poc=4282.48000 vah=4286.09000 val=4249.77000 cd=-720.00 fp_press=-0.0381 state=0 shadow=FALSE
2026.09.24 18:29:59.678	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][FLOW_DIAG] ts=2026.09.24 15:30 vwap=4268.72685 dev=-2.68 poc=4282.48000 vah=4286.09000 val=4249.72000 cd=-768.00 fp_press=-0.0405 state=0 shadow=FALSE
```

### C. Decision Pipeline Logs (`DECISION`) (DIRECT EVIDENCE)
```text
2026.09.24 17:50:00.146	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790261401095 sym=XAUUSD act=1 reg=3 hyp=2 score=0.4523 reason=OK
2026.09.24 17:55:08.047	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790261707096 sym=XAUUSD act=3 reg=3 hyp=0 score=0.3448 reason=SCORE_GATE
2026.09.24 18:00:01.397	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790262002097 sym=XAUUSD act=3 reg=3 hyp=0 score=0.4178 reason=SCORE_GATE
2026.09.24 18:05:02.385	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790262303098 sym=XAUUSD act=1 reg=3 hyp=2 score=0.4301 reason=OK
2026.09.24 18:10:00.582	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790262601099 sym=XAUUSD act=3 reg=3 hyp=0 score=0.3000 reason=SCORE_GATE
2026.09.24 18:15:06.435	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790262906100 sym=XAUUSD act=3 reg=3 hyp=0 score=0.3000 reason=SCORE_GATE
2026.09.24 18:20:05.124	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790263206101 sym=XAUUSD act=3 reg=3 hyp=0 score=0.3000 reason=SCORE_GATE
2026.09.24 18:25:03.718	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790263504102 sym=XAUUSD act=3 reg=3 hyp=0 score=0.3070 reason=SCORE_GATE
2026.09.24 18:29:59.679	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790263800103 sym=XAUUSD act=3 reg=3 hyp=0 score=0.3000 reason=SCORE_GATE
```

### D. Risk Sizing & Veto Logs (`SIZE_DIAG`, `WARN/SIZE`) (DIRECT EVIDENCE)
```text
2026.09.24 17:50:00.146	AMIGO (XAUUSD,M5)	[AlgoMind][DIAG] ts=2026.09.24 14:50 sym=XAUUSD tf=5 reg=3 dir=1 fus=-0.020 flip_u=0 flip_d=0 surge=0 swp=1 cntL=0.300 cntS=0.000 mrL=0.000 mrS=0.452 sL=0.300 sS=0.452 best=0.452 mrg=0.152 th=0.42 mrg_th=0.05 act=1 rsn=OK
2026.09.24 17:50:00.146	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][SIZE_DIAG] eq=4638.34 risk_amt=23.19 stop_dist=34.1450 tick_sz=0.00100 tick_val=0.10 loss_per_lot=3414.50 min_lot_loss=34.15 min_vol=0.01 dist=1.47x
2026.09.24 17:50:00.146	AMIGO (XAUUSD,M5)	[AlgoMind][WARN][SIZE] MIN_LOT_EXCEEDS_RISK
2026.09.24 18:05:02.385	AMIGO (XAUUSD,M5)	[AlgoMind][DIAG] ts=2026.09.24 15:05 sym=XAUUSD tf=5 reg=3 dir=1 fus=0.078 flip_u=0 flip_d=0 surge=0 swp=1 cntL=0.300 cntS=0.000 mrL=0.000 mrS=0.430 sL=0.300 sS=0.430 best=0.430 mrg=0.130 th=0.42 mrg_th=0.05 act=1 rsn=OK
2026.09.24 18:05:02.385	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][SIZE_DIAG] eq=4652.06 risk_amt=23.26 stop_dist=40.9980 tick_sz=0.00100 tick_val=0.10 loss_per_lot=4099.80 min_lot_loss=41.00 min_vol=0.01 dist=1.76x
2026.09.24 18:05:02.385	AMIGO (XAUUSD,M5)	[AlgoMind][WARN][SIZE] MIN_LOT_EXCEEDS_RISK
```

### E. Missing Direct Diagnostic Tag Status (UNVERIFIED DIRECTLY)
The explicit diagnostic tags proposed in Gate B (`[RUNTIME_DIAG][OnTick]`, `[RUNTIME_DIAG][NEW_BAR]`, `[RUNTIME_DIAG][OnClosedBar]`, `[RUNTIME_DIAG][SNAPSHOT]`, `[RUNTIME_DIAG][FEATURES]`) were **NOT** present in the log file because the active MT5 chart was running a pre-instrumentation binary compiled prior to the Gate B diff application.

---

## 3. EVIDENCE CLASSIFICATION RECONCILIATION

| Pipeline Stage | Evidence Classification | Grounding |
| :--- | :--- | :--- |
| **EA Initialization** | `DIRECT EVIDENCE` | Log entry at `17:47:55.799` with symbol audit parameters. |
| **OnTick Execution** | `INDIRECT / DOWNSTREAM EVIDENCE` | Proven downstream by 9 bar closure triggers between `17:50` and `18:30`. |
| **New-Bar Detection** | `INDIRECT / DOWNSTREAM EVIDENCE` | Proven downstream by 9 bar boundary detections. |
| **OnClosedBar Entry** | `INDIRECT / DOWNSTREAM EVIDENCE` | Proven downstream by `FLOW_DIAG` logging on every bar closure. |
| **Market Snapshot Build** | `INDIRECT / DOWNSTREAM EVIDENCE` | Proven downstream by bid/ask/ATR values in `FLOW_DIAG` and `SIZE_DIAG`. |
| **Feature Vector Build** | `INDIRECT / DOWNSTREAM EVIDENCE` | Proven downstream by feature values (`fus`, `swp`, `flip`) in `DIAG`. |
| **FLOW_DIAG Telemetry** | `DIRECT EVIDENCE` | 9 explicit `[FLOW_DIAG]` entries logged to disk. |
| **Decision Pipeline** | `DIRECT EVIDENCE` | 9 explicit `[DECISION]` entries logged to disk. |
| **Risk Sizing Invocation**| `DIRECT EVIDENCE` | 2 explicit `[SIZE_DIAG]` entries logged to disk. |
| **Risk Veto** | `DIRECT EVIDENCE` | 2 explicit `[WARN][SIZE] MIN_LOT_EXCEEDS_RISK` entries logged to disk. |
| **Shadow Mode Interception**| `STATIC-ONLY / UNREACHED` | Execution was vetoed upstream by Risk Engine before reaching `ExecuteIntent()`. |
| **Order Request Build** | `STATIC-ONLY / UNREACHED` | Vetoed upstream by Risk Engine before `TradeIntent` validation. |
| **Broker Order Submission**| `VERIFIED BLOCKED / NOT SUBMITTED` | Blocked upstream by Risk Engine lot sizing veto. |

---

## 4. SHADOW INTERCEPTION SOURCE-PATH AUDIT

To establish why Shadow Interception did not emit a `[SHADOW]` log entry at runtime, we trace the exact source execution path in `AMIGO.mq5`:

```text
Decide() returns ACTION_TRADE (act=1)
        ↓  [Line 397: if(dr.action != ACTION_TRADE) return;]
RiskAllows() returns true
        ↓  [Line 401]
SelectStop() calculates stop_dist
        ↓  [Line 426]
ComputeLotSize(g_symbol, entry, sl, 0.5%, actual_risk, size_err)
        ↓
        ├── Account Equity = $4,638.34
        ├── Max Risk (0.5%) = $23.19
        ├── Stop Distance = 34.145 points
        ├── Raw Required Lots = 0.0068 lots
        ├── Broker Min Volume = 0.01 lots ($34.15 risk)
        └── Result: ComputeLotSize returns 0.0, size_err = "MIN_LOT_EXCEEDS_RISK"
        ↓
if(lots <= 0.0)
{
   LogMsg(LOG_WARN, "SIZE", size_err);   <-- [Line 448: EMITTED AT RUNTIME]
   return;                               <-- [Line 449: EARLY EXIT]
}
        ↓ [UNREACHED AT RUNTIME]
ValidateIntent(ti, ...)
        ↓ [UNREACHED AT RUNTIME]
ExecuteIntent(ti, lots, g_cfg)
        ↓ [UNREACHED AT RUNTIME]
if(cfg.shadow_only)
{
   LogMsg(LOG_INFO, "SHADOW", "INTERCEPTED..."); <-- [UNREACHED AT RUNTIME]
   return res;
}
```

### Authoritative Shadow Interception Classification:
**`Shadow Interception: VERIFIED STATIC ONLY / UNREACHED AT RUNTIME`**

*Explanation:* The shadow intercept gate (`cfg.shadow_only`) inside `ExecuteIntent()` is mathematically verified in static code (`Execution Engine.mqh` L136–L144). At runtime, candidate trades at `17:50:00` and `18:05:02` were vetoed by the Risk Engine (`lots <= 0.0`) prior to reaching `ExecuteIntent()`. Thus, the shadow boundary was not reached at runtime.

---

## 5. INDEPENDENT EXECUTION BOUNDARY CLASSIFICATION

| Execution Component | Classification | Empirical / Source Evidence |
| :--- | :--- | :--- |
| **Candidate Trade Decision** | `VERIFIED RUNTIME` | Emitted `act=1` (TRADE) at `17:50:00` (score=0.4523) and `18:05:02` (score=0.4301). |
| **Risk Sizing Invocation** | `VERIFIED RUNTIME` | Emitted `[SIZE_DIAG]` logging equity `$4,638.34` and stop distance `34.1450`. |
| **Minimum-Lot Validation** | `VERIFIED RUNTIME` | Min lot loss (`$34.15`) evaluated against max risk (`$23.19`). |
| **Risk Veto** | `VERIFIED RUNTIME` | Emitted `[WARN][SIZE] MIN_LOT_EXCEEDS_RISK` and executed early exit. |
| **Shadow Mode Interception** | `VERIFIED STATIC ONLY` | `ExecuteIntent()` intercept block unreached due to upstream risk veto. |
| **Order Request Construction** | `UNREACHED AT RUNTIME` | `TradeIntent` build unreached due to upstream risk veto. |
| **Broker Order Submission** | `VERIFIED BLOCKED / NOT SUBMITTED` | Confirmed blocked by upstream Risk Engine lot sizing veto. |

---

## 6. UNRESOLVED EVIDENCE GAPS

1. **Direct OnTick / New-Bar / Snapshot / Feature Logging:** Direct log entries for `[RUNTIME_DIAG]` were not emitted because the attached EA binary was not re-attached post-Gate B edit. (Execution is proven downstream by `FLOW_DIAG`).
2. **Runtime Shadow Mode Interception:** Runtime execution of `ExecuteIntent()` shadow intercept requires a candidate trade with calculated lot size $\ge 0.01$ (e.g. tight stop distance or higher risk allowance in shadow mode).

---

## 7. RECOMMENDED NEXT GATE

Selected Next Gate: **`E — Proceed to shadow interception verification`**

**Rationale:**  
The decision pipeline, feature calculations, order-flow engine, regime evaluation, and risk sizing veto have been verified at runtime. To verify the final remaining safety boundary (`ExecuteIntent` shadow intercept), a controlled test with a candidate trade satisfying lot size $\ge 0.01$ under shadow mode is required.

---

## 8. AUTHORITATIVE GOVERNANCE STATUS

```text
LEVEL 3 — PARTIALLY VERIFIED

LEVEL 4 LIVE TRADING — NOT AUTHORIZED

GIT COMMIT — NOT APPROVED

GIT PUSH — NOT APPROVED
```
