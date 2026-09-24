# ALGOMIND PHASE 6 — OPTION B: CONTROLLED NON-LIVE SHADOW INTERCEPTION VERIFICATION REPORT

**Project:** AlgoMind / ASAP Retail Order-Flow System  
**Symbol / Timeframe:** `XAUUSD` / `M5`  
**Execution Environment:** Windows 10, MetaTrader 5 (PID 7964), Exness Demo (`Exness-MT5Trial`)  
**Operating Mode:** SHADOW MODE (`InpShadowOnly = true`)  
**Report Date:** 2026-09-24  
**Local Execution Time:** 2026-09-24 19:33:00+03:00  

---

## 1. PRIMARY TEST OBJECTIVE

The primary objective of this Option B test is to attempt runtime verification of the `ExecuteIntent()` shadow-only interception boundary (`g_cfg.shadow_only`) under strict, non-negotiable safety constraints:
1. Preserve `InpShadowOnly = true` at all times.
2. Maintain 100% intact Risk Engine calculations, minimum-lot sizing validations, and drawdown gates.
3. Do not alter strategy scoring logic, regime evaluation, or entry/exit rules.
4. Do not manufacture a pass by hardcoding lot sizes or bypassing risk checks.
5. If no candidate trade satisfies production risk/sizing constraints ($\ge 0.01$ lots) to reach `ExecuteIntent()`, report the shadow gate as `NOT REACHED / VERIFIED STATIC ONLY` without forcing execution.

---

## 2. PRE-TEST ENVIRONMENT AUDIT

| Environment Field | Recorded Value / Verification Source |
| :--- | :--- |
| **Account Login** | Demo Account (Exness Demo Server) |
| **Account Type** | Demo (`Exness-MT5Trial`) |
| **Broker** | Exness Technologies Ltd |
| **Server** | `Exness-MT5Trial` |
| **Symbol** | `XAUUSD` |
| **Chart Timeframe** | `PERIOD_M5` (5-minute execution timeframe) |
| **EA Version / Build** | `AMIGO.ex5` (88,074 bytes) |
| **Compilation Timestamp** | `2026.09.24 08:49:34 AM` |
| **EA Attachment Timestamp**| `2026.09.24 17:47:55.799 AM` |
| **InpShadowOnly** | `true` (`g_cfg.shadow_only = true`) |
| **Risk Percentage** | `0.5%` per trade |
| **Daily Risk Limit** | `2.0%` hard daily drawdown limit |
| **Total Risk Limit** | `5.0%` hard total drawdown limit |
| **Minimum Volume** | `0.01` lots |
| **Volume Step** | `0.01` lots |
| **Stop-Loss Configuration**| Structural Swing ATR-based (`SelectStop`) |
| **Current Equity** | `$4,636.90` – `$4,652.06` |
| **Free Margin** | `$4,636.90` |

---

## 3. SAFETY CONFIGURATION ASSURANCE

- **Non-Live Confirmation:** Confirmed attached to `Exness-MT5Trial` Demo account. No live money or live trading account attached.
- **Shadow Mode Enforced:** `InpShadowOnly = true` verified active in input configuration and source code.
- **Zero Logic Modification:** No code changes made to strategy scoring, regime thresholds, risk sizing calculations, or execution routines.
- **Git State:** 0 commits, 0 pushes approved.

---

## 4. OBSERVATION PERIOD AND CANDIDATE STATISTICS

- **Observation Start:** `2026.09.24 17:47:55`
- **Observation End:** `2026.09.24 19:30:01`
- **M5 Boundaries Observed:** 21 consecutive 5-minute candle closures
- **`ACTION_TRADE` Candidates Generated:** 3 (`17:50:00`, `18:05:02`, `18:55:00`)
- **Risk Engine Vetoes (`MIN_LOT_EXCEEDS_RISK`):** 3
- **Candidates Reaching `ExecuteIntent()`:** 0
- **Shadow-Only Interceptions:** 0
- **`OrderSend` Attempts:** 0
- **Live Broker Orders Submitted:** 0

---

## 5. RAW RUNTIME EVIDENCE & LOG EXCERPTS

### Candidate 1 (17:50:00.146):
```text
2026.09.24 17:50:00.146	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790261401095 sym=XAUUSD act=1 reg=3 hyp=2 score=0.4523 reason=OK
2026.09.24 17:50:00.146	AMIGO (XAUUSD,M5)	[AlgoMind][DIAG] ts=2026.09.24 14:50 sym=XAUUSD tf=5 reg=3 dir=1 fus=-0.020 flip_u=0 flip_d=0 surge=0 swp=1 cntL=0.300 cntS=0.000 mrL=0.000 mrS=0.452 sL=0.300 sS=0.452 best=0.452 mrg=0.152 th=0.42 mrg_th=0.05 act=1 rsn=OK
2026.09.24 17:50:00.146	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][SIZE_DIAG] eq=4638.34 risk_amt=23.19 stop_dist=34.1450 tick_sz=0.00100 tick_val=0.10 loss_per_lot=3414.50 min_lot_loss=34.15 min_vol=0.01 dist=1.47x
2026.09.24 17:50:00.146	AMIGO (XAUUSD,M5)	[AlgoMind][WARN][SIZE] MIN_LOT_EXCEEDS_RISK
```

### Candidate 2 (18:05:02.385):
```text
2026.09.24 18:05:02.385	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790262303098 sym=XAUUSD act=1 reg=3 hyp=2 score=0.4301 reason=OK
2026.09.24 18:05:02.385	AMIGO (XAUUSD,M5)	[AlgoMind][DIAG] ts=2026.09.24 15:05 sym=XAUUSD tf=5 reg=3 dir=1 fus=0.078 flip_u=0 flip_d=0 surge=0 swp=1 cntL=0.300 cntS=0.000 mrL=0.000 mrS=0.430 sL=0.300 sS=0.430 best=0.430 mrg=0.130 th=0.42 mrg_th=0.05 act=1 rsn=OK
2026.09.24 18:05:02.385	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][SIZE_DIAG] eq=4652.06 risk_amt=23.26 stop_dist=40.9980 tick_sz=0.00100 tick_val=0.10 loss_per_lot=4099.80 min_lot_loss=41.00 min_vol=0.01 dist=1.76x
2026.09.24 18:05:02.385	AMIGO (XAUUSD,M5)	[AlgoMind][WARN][SIZE] MIN_LOT_EXCEEDS_RISK
```

### Candidate 3 (18:55:00.277):
```text
2026.09.24 18:55:00.277	AMIGO (XAUUSD,M5)	[AlgoMind][DECISION] id=1790265301108 sym=XAUUSD act=1 reg=3 hyp=2 score=0.4251 reason=OK
2026.09.24 18:55:00.277	AMIGO (XAUUSD,M5)	[AlgoMind][INFO][SIZE_DIAG] eq=4636.90 risk_amt=23.18 stop_dist=33.8130 tick_sz=0.00100 tick_val=0.10 loss_per_lot=3381.30 min_lot_loss=33.81 min_vol=0.01 dist=1.46x
2026.09.24 18:55:00.277	AMIGO (XAUUSD,M5)	[AlgoMind][WARN][SIZE] MIN_LOT_EXCEEDS_RISK
```

---

## 6. CANDIDATE-BY-CANDIDATE EXECUTION-PATH TABLE

| Candidate ID | Time | Decision | Risk Sizing | Min Lot Loss vs Risk | Action Taken | Reached ExecuteIntent? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `1790261401095` | `17:50:00` | `act=1` (TRADE) | Stop=34.1450 | `$34.15` > `$23.19` (0.5%) | `MIN_LOT_EXCEEDS_RISK` Veto | **NO** (Exited L449) |
| `1790262303098` | `18:05:02` | `act=1` (TRADE) | Stop=40.9980 | `$41.00` > `$23.26` (0.5%) | `MIN_LOT_EXCEEDS_RISK` Veto | **NO** (Exited L449) |
| `1790265301108` | `18:55:00` | `act=1` (TRADE) | Stop=33.8130 | `$33.81` > `$23.18` (0.5%) | `MIN_LOT_EXCEEDS_RISK` Veto | **NO** (Exited L449) |

---

## 7. STAGE-BY-STAGE EVIDENCE CLASSIFICATION MATRIX

| Stage | Classification | Direct Evidence | Notes |
| :--- | :--- | :--- | :--- |
| **Candidate decision** | `VERIFIED RUNTIME — DIRECT` | `[DECISION] act=1` | Logged at 17:50, 18:05, and 18:55. |
| **RiskAllows** | `VERIFIED RUNTIME — DIRECT` | `RiskAllows() == true` | Passed, allowing execution to reach sizing. |
| **Risk sizing** | `VERIFIED RUNTIME — DIRECT` | `[SIZE_DIAG] eq=4636.90` | Calculated max risk (\$23.18–\$23.26). |
| **Minimum-lot validation**| `VERIFIED RUNTIME — DIRECT` | `[WARN][SIZE] MIN_LOT...` | Min lot loss (\$33.81–\$41.00) > max risk. |
| **ExecuteIntent entry** | `NOT REACHED` | None | Vetoed upstream at line 449. |
| **Shadow gate entry** | `NOT REACHED` | None | Vetoed upstream at line 449. |
| **Shadow interception** | `VERIFIED STATIC ONLY` | `Execution Engine.mqh` L137 | Verified in static code; unreached at runtime. |
| **OrderSend entry** | `NOT REACHED` | None | Vetoed upstream at line 449. |
| **Broker submission** | `NOT REACHED` | None | 0 orders submitted to broker. |

---

## 8. ALTERNATE-PATH SEARCH RESULTS

A complete static search for `OrderSend` across `AMIGO.mq5` and all included header files confirmed:
- `OrderSend` is called **ONLY** in `Include/Execution Engine.mqh` at line 147.
- Line 147 is strictly protected by the `if(g_cfg.shadow_only)` return gate at line 137.
- No alternate trade functions, hidden order wrappers, or secondary submission loops exist in the codebase.

---

## 9. ENVIRONMENTAL LIMITATIONS AND UNRESOLVED GAPS

1. **Environmental Limitation:** On an account with `$4,636` equity and 0.5% risk allowance (`$23.18`), any XAUUSD stop distance greater than `23.18` points requires less than `0.01` lots. Because XAUUSD M5 ATR / swing stop distances naturally exceed 30 points (`33.8` to `41.0` points), `ComputeLotSize()` correctly and safely vetoes 100% of candidate trades.
2. **Strict Compliance with Governance:** Per Mandatory Constraint #4 & #5, risk settings were not altered, minimum volume was not lowered, and synthetic lot sizes were not hardcoded. Consequently, runtime execution of `ExecuteIntent()` shadow logging remains **`VERIFIED STATIC ONLY`**.

---

## 10. RECOMMENDED NEXT GATE

Selected Next Gate: **`E — Proceed to shadow interception verification`** (Requires an environment where account equity/balance or symbol specifications allow candidate lot sizing $\ge 0.01$ lots without violating production risk limits).

---

## 11. MANDATORY FINAL STATUS BLOCK

```text
OPTION B RESULT:
INCONCLUSIVE

CANDIDATE PATH:
NOT OBSERVED

SHADOW INTERCEPTION:
VERIFIED STATIC ONLY

ORDER SEND:
NOT REACHED

LIVE ORDERS SUBMITTED:
0 — VERIFIED SAFE (ALL CANDIDATES BLOCKED UPSTREAM BY RISK ENGINE)

GLOBAL BROKER-SUBMISSION SAFETY:
NOT VERIFIED UNLESS ALL RELEVANT EXECUTION PATHS ARE DIRECTLY COVERED

LEVEL 3 STATUS:
PARTIALLY VERIFIED

LEVEL 4 LIVE TRADING:
NOT AUTHORIZED

GIT COMMIT:
NOT APPROVED

GIT PUSH:
NOT APPROVED
```
