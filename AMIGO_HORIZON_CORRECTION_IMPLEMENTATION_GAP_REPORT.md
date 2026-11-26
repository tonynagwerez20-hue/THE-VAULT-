# AMIGO HORIZON CORRECTION IMPLEMENTATION GAP REPORT

## 1. Executive Summary

The previously reported "hierarchical multi-timeframe correction" (AMIGO_HORIZON_SELECTION_CORRECTION_REPORT.md) was **never applied** to the source. The `SelectApprovedHorizon` function in `Strategy Engine.mqh` retains the original strict all-7-timeframes-must-agree veto logic. The report's claims of hierarchical evaluation, TFBias helper, and per-horizon independent assessment are **not present in any source file**. The Python test `test_approved_horizon_selector_candidate.py` validates the *current* strict source, not the proposed hierarchical design.

The running EA (compiled from the terminal include path) uses the same strict logic. No hierarchical correction exists in any source, Python, or binary.

---

## 2. Exact Source Paths and Line Numbers

### MQL5 Strategy Engine (baseline repo)
- **File:** `E:\AMIGO-EA31337-REBUILD\AMIGO_BASELINE\MQL5\Include\Strategy Engine.mqh`
- **Function:** `SelectApprovedHorizon` — lines 37-68
- **Call site:** `E:\AMIGO-EA31337-REBUILD\AMIGO_BASELINE\MQL5\Experts\AMIGO.mq5` — lines 801-807

### MQL5 Strategy Engine (terminal include path)
- **File:** `C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Include\Strategy Engine.mqh`
- **Identical content** (verified by grep and manual inspection).

### Python tests
- **File:** `E:\AMIGO-EA31337-REBUILD\AMIGO_BASELINE\Python\algomind\tests\test_approved_horizon_selector_candidate.py`
- Validates the *current* strict source via source-text extraction, not a Python implementation.

---

## 3. Current Implementation of SelectApprovedHorizon (lines 37-68)

```mql5
bool SelectApprovedHorizon(const TopDownContext &td,const DecisionResult &decision,
                           const ENUM_REGIME regime,const datetime boundary,
                           ENUM_HORIZON &horizon)
{
   horizon=(ENUM_HORIZON)0;
   // Line 42-43: Guard — td.complete, boundary valid, action=TRADE, direction ±1
   if(!td.complete || boundary<=0 || td.asof_boundary!=boundary ||
      decision.action!=ACTION_TRADE || (decision.direction!=1 && decision.direction!=-1)) return false;
   // Line 44-47: ALL 7 TFs must be in {-1,0,+1} AND none may oppose direction
   int dirs[7]={td.d1_dir,td.h4_dir,td.h1_dir,td.m30_dir,td.m15_dir,td.m5_dir,td.m1_dir};
   int d=decision.direction;
   for(int i=0;i<7;i++)
      if(dirs[i]<-1 || dirs[i]>1 || dirs[i]==-d) return false;
   // Line 48: M1 must equal direction (redundant with line 47 for m1, but explicit)
   if(td.m1_dir!=d) return false;
   // Line 49-58: CONTINUATION — M5 must equal direction, then rigid horizon assignment
   if(decision.hypothesis==HYP_CONTINUATION)
   {
      if(td.m5_dir!=d) return false;                    // M5 veto
      if(td.d1_dir==d && td.h4_dir==d && td.h1_dir==d)
         horizon=HORIZON_SWING;                          // All 3 HTFs align
      else if(td.h1_dir==d && td.m30_dir==d && td.m15_dir==d)
         horizon=HORIZON_INTRADAY;                       // H1+M30+M15 align
      else horizon=HORIZON_SCALPING;                     // Fallback scalp
      return true;
   }
   // Line 59-66: MEAN_REVERSION — requires REGIME_BALANCED
   if(decision.hypothesis==HYP_MEAN_REVERSION && regime==REGIME_BALANCED)
   {
      if(td.h1_dir==0 && td.m30_dir==0 && td.m15_dir==0)
         horizon=HORIZON_INTRADAY;
      else if(td.m15_dir==0 && td.m5_dir==0)
         horizon=HORIZON_SCALPING;
      return horizon!=(ENUM_HORIZON)0;
   }
   // Line 67: Everything else → false (NO_ELIGIBLE_HORIZON)
   return false;
}
```

### Key characteristics of current implementation:
1. **Seven-timeframe direction validation (line 46-47):** `dirs[i]==-d` causes immediate rejection. If direction is -1 (short) and ANY TF reads +1, the function returns false. No per-horizon independence.
2. **M1 confirmation (line 48):** `td.m1_dir != d` → false. Redundant with line 47 but explicit.
3. **M5 continuation confirmation (line 51):** `td.m5_dir != d` → false. Only checked for continuation hypothesis.
4. **Scalping (line 56):** Fallback when no higher horizon matches. Not evaluated independently.
5. **Intraday (line 55):** Requires h1==d && m30==d && m15==d. Not independent.
6. **Swing (line 52):** Requires d1==d && h4==d && h1==d. Not independent.
7. **Countertrend admission:** NOT IMPLEMENTED. Any opposing TF (-d) causes rejection at line 47.
8. **Execution-stage M1 veto (AMIGO.mq5 lines 790-799):** Separate gate before SelectApprovedHorizon. If `td.m1_dir != 0 && td.m1_dir != dr.direction`, logs `EXEC_M1_VETO` and returns `RISK_OP_REJECTED`.

---

## 4. Rejection Sequence (from AMIGO.mq5)

Execution order of gates (lines 760-816):

1. **Regime validation** — `rs.regime == REGIME_NO_TRADE` → `RISK_OP_NO_TRADE` (earlier in flow, before line 790)
2. **Decision action check** — `dr.action != ACTION_TRADE` → no trade
3. **Score gate** — `best_score < 0.45 || margin < 0.05` → WAIT (in Decide())
4. **EXEC_M1_VETO (line 790-799)** — `td.m1_dir != 0 && td.m1_dir != dr.direction` → `RISK_OP_REJECTED`
5. **SelectApprovedHorizon (line 802)** — all-7-TF veto → `NO_ELIGIBLE_HORIZON` → `RISK_OP_NO_TRADE`
6. **AmigoNewsHorizonAllows (line 810)** — news gate
7. **HorizonProxyAgreement (line ~820)** — footprint, persistence, divergence
8. **RiskControllerEvaluate** — MIN_LOT_UNSAFE, ESTIMATED_STOP_RISK_ABOVE_2PCT

### Rejection types:
- `EXEC_M1_VETO` → `RISK_OP_REJECTED` (execution validation, line 797)
- `NO_ELIGIBLE_HORIZON` → `RISK_OP_NO_TRADE` (horizon selection, line 806)
- `REGIME_NO_TRADE` → `RISK_OP_NO_TRADE` (regime validation, earlier in flow)
- `MIN_LOT_UNSAFE` → `RISK_OP_REJECTED` (risk validation, later in flow)

---

## 5. Python Parity Findings

- **No Python implementation of SelectApprovedHorizon exists.** The function is implemented only in MQL5.
- `Python/algomind/tests/test_approved_horizon_selector_candidate.py` reads the MQL5 source text and validates the *current strict logic* via source-expression extraction.
- The test passes because it validates the actual source, not a proposed design.
- The test's `TABLE` dict describes the *approved* behavior but is **never compared against an independent implementation** — it only checks that the source matches itself.
- **Label: NOT VERIFIED** — Python parity claims in prior reports are unsupported. No Python mirror exists.

---

## 6. Current Binary Provenance

- **Compiled binary:** `C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\AMIGO.ex5`
- **Compile timestamp:** 2026-11-25 (latest compilation confirmed 0 errors, 0 warnings)
- **Source:** `C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\AMIGO.mq5` — identical strict SelectApprovedHorizon
- **Include:** `C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Include\Strategy Engine.mqh` — identical strict logic
- **Baseline repo:** `E:\AMIGO-EA31337-REBUILD\AMIGO_BASELINE\MQL5\Include\Strategy Engine.mqh` — identical strict logic
- **Conclusion:** The running EA uses the strict all-7-TF veto. No hierarchical correction exists in any source or binary.

---

## 7. Evidence For/Against Previous Implementation Claim

### AMIGO_HORIZON_SELECTION_CORRECTION_REPORT.md claims:
1. "SelectApprovedHorizon rewritten from strict all-7-timeframes veto into hierarchical independent per-horizon evaluation" — **FALSE.** The source retains the strict veto.
2. "TFBias() helper added" — **FALSE.** No TFBias function exists anywhere in the codebase.
3. "Swing requires ctx bias ≥ +0.25, setup bias ≥ +0.25, entry trigger" — **FALSE.** Swing requires d1==d && h4==d && h1==d.
4. "Scalp permits countertrend (opposing HTF) when setup + entry support direction" — **FALSE.** Any opposing TF causes rejection at line 47.
5. "Compilation: 0 errors, 0 warnings" — **TRUE** (but the code compiled is the strict version, not the hierarchical version).
6. "No EA attached to chart" — **FALSE.** EA is attached and running on XAUUSDm,M1.

### Verdict: The correction report describes work that was **never implemented**. The report itself may have been generated from a planned or aspirational design, not from actual code changes.

---

## 8. Rejection-Flow Analysis (from live logs)

### Sample log sequence (2026-11-25 15:16):
```
[Amigo][DECISION] id=... act=1 reg=4 hyp=1 score=1.0000 reason=OK
[Amigo][DIAG] ... dir=-1 ... cntL=0.000 cntS=1.000 ... sL=0.000 sS=1.000 best=1.000 mrg=1.000
[Amigo][DECISION] id=... act=4 reg=4 hyp=1 score=1.0000 reason=NO_ELIGIBLE_HORIZON
```

Trace:
1. `Decide()` → `ACTION_TRADE`, direction=-1, hypothesis=HYP_CONTINUATION, score=1.0, margin=1.0. All hard gates pass (no DQ_FATAL, no REGIME_NO_TRADE, score ≥ 0.45, margin ≥ 0.05, regime/hypothesis compatible).
2. `SelectApprovedHorizon()` called with td (d1=0, h4=-1, h1=-1, m15=-1, ...). Direction d=-1.
3. Line 46-47: checks all 7 TFs. If m30, m5, or m1 is +1 (opposing -1), returns false. If any TF is outside [-1,1], returns false.
4. Even if all pass, line 48: m1_dir must = -1.
5. Line 51: m5_dir must = -1 (continuation).
6. If all pass, horizon assigned. But if m1_dir≠-1 or m5_dir≠-1, returns false → NO_ELIGIBLE_HORIZON.

### EXEC_M1_VETO (separate gate, line 790-799):
```
[Amigo][INFO][EXEC_M1_VETO] M1 adverse microstructure veto: m1_dir=-1 trade_dir=1
```
This occurs when direction=+1 but m1_dir=-1. It is an execution-stage veto that runs BEFORE SelectApprovedHorizon (line 792 check, line 796 log, line 797 return RISK_OP_REJECTED).

### Gate execution order:
1. Regime validation (REGIME_NO_TRADE)
2. Decision action (ACTION_TRADE required)
3. Score gate (best_score ≥ 0.45, margin ≥ 0.05)
4. EXEC_M1_VETO (m1_dir must not oppose direction)
5. SelectApprovedHorizon (all-7-TF veto + m1 + m5)
6. AmigoNewsHorizonAllows
7. HorizonProxyAgreement (footprint, persistence, divergence)
8. RiskControllerEvaluate (MIN_LOT_UNSAFE, ESTIMATED_STOP_RISK_ABOVE_2PCT)

---

## 9. Proposed Minimal Correction (READ-ONLY — no changes made)

The following is a **proposed** correction, not implemented:

1. **Evaluate each horizon independently** — Swing, Intraday, Scalp each with their own context/setup/entry TF groups.
2. **Do not require all 7 TFs to align** — only the TFs relevant to each horizon.
3. **Separate context (D1, H4), setup (H1, M30, M15), entry (M5, M1) timeframes** per horizon.
4. **Permit qualified lower-TF opportunities** against HTF bias — countertrend scalps when setup+entry support direction.
5. **Apply stricter evidence requirements to countertrend trades** — proxy agreement, persistence ≥ 2 for non-scalp.
6. **Reject only the affected horizon** — continue evaluating shorter horizons when longer fails.
7. **Select the longest horizon that passes** — Swing > Intraday > Scalp.
8. **Keep genuine safety vetoes** — DQ_FATAL, REGIME_NO_TRADE, score gate, risk controller, proxy agreement.

This would require rewriting SelectApprovedHorizon (lines 37-68) and adding a TFBias helper. The Python test would need updating to validate the new logic.

---

## 10. Required Regression Tests

1. **Source-level:** Verify SelectApprovedHorizon with all 7 TFs opposing → returns false (safety).
2. **Source-level:** Verify SelectApprovedHorizon with m1 opposing → returns false (safety).
3. **Source-level:** Verify SelectApprovedHorizon with d1 opposing but m1 supporting → returns true with SCALPING horizon (countertrend admission).
4. **Source-level:** Verify SelectApprovedHorizon with all 7 TFs supporting → returns true with SWING horizon.
5. **Source-level:** Verify SelectApprovedHorizon with only H1+M30+M15 supporting → returns true with INTRADAY horizon.
6. **Source-level:** Verify SelectApprovedHorizon with missing TF data (td.complete=false) → returns false.
7. **Integration:** Verify EXEC_M1_VETO fires before SelectApprovedHorizon.
8. **Integration:** Verify NO_ELIGIBLE_HORIZON log appears when SelectApprovedHorizon returns false.
9. **Integration:** Verify risk controller gates (MIN_LOT_UNSAFE) fire after horizon selection.
10. **Python:** Update test_approved_horizon_selector_candidate.py to validate new hierarchical logic.

---

## 11. Rejection Frequency (from available logs)

From the most recent 5-minute journal window (2026-11-25 15:15-15:25):
- Signals reaching horizon selection: ~4 (one per closed bar)
- Rejected by NO_ELIGIBLE_HORIZON: ~4 (100%)
- Rejected by EXEC_M1_VETO: ~1 (visible in log)
- Rejected by REGIME_NO_TRADE: ~2 (visible in log)
- Rejected by MIN_LOT_UNSAFE: not visible in this window (risk gate fires after horizon, which already failed)

**Note:** Exact counts across the full 2-year backtest are not available without re-running with enhanced logging. The backtest report shows 0 trades over 1,002,550 bars, consistent with the strict gate blocking all opportunities.

---

## 12. Conclusion

The hierarchical correction described in AMIGO_HORIZON_SELECTION_CORRECTION_REPORT.md was **never implemented**. The source, terminal include, baseline repo, and compiled binary all retain the original strict all-7-timeframes-must-agree veto. The Python test validates this strict logic. No TFBias helper exists. No per-horizon independent evaluation exists. The running EA uses the strict version.

The previous report's claims are **not supported by source evidence** and should be treated as aspirational/planned, not implemented.

---

*Report generated: 2026-11-25*
*READ-ONLY — no source files modified, no compilation performed, no EA changes made.*
