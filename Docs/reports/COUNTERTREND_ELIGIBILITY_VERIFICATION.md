# AMIGO — Countertrend Eligibility Verification Report

**Document Date:** 2026-11-02  
**Target Code:** `MQL5/Include/Regime Engine.mqh` (Lines 85–95, 181–184)  
**Evaluator:** Antigravity Quantitative Trading Systems Engineer  

---

## 1. Exhaustion Gate Logic Specification

Countertrend trades in AMIGO belong to the `HYP_MEAN_REVERSION` hypothesis under `REGIME_EXHAUSTION`. The mathematical scoring of exhaustion is defined in `ScoreExhaustion()`:

```mql5
double ScoreExhaustion(const FeatureSnapshot &f, const TopDownContext &td)
{
   // Strict conjunctive countertrend gating: requires confirmed sweep reject AND >= 2.0 ATR extension
   if(!f.sweep_reject || MathAbs(f.dev_vwap_atr) < 2.0)
      return 0.0;

   double div = Clip01(f.delta_divergence);
   double ext = Clip01((MathAbs(f.dev_vwap_atr) - 2.0) / 2.0);
   return 0.50 + 0.25*div + 0.25*ext;
}
```

### Conjunctive Dual Condition:
1. **Condition A (`f.sweep_reject`):** Confirmed liquidity sweep with price rejection.
2. **Condition B (`MathAbs(f.dev_vwap_atr) >= 2.0`):** Severe price extension beyond 2.0 ATR from session VWAP.

If **either** condition fails, the score returns `0.0`. Only when **both** conditions are satisfied does the base score start at `0.50`, scaling up to `1.00` based on order flow divergence (`delta_divergence`) and extreme extension beyond 2.0 ATR.

---

## 2. Condition-by-Condition Truth Table

| `f.sweep_reject` | `\|dev_vwap_atr\|` | `delta_divergence` | Score | Threshold (0.60) Reachable? | Eligible for `REGIME_EXHAUSTION`? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `false` | 0.8 ATR | Any | **0.00** | No | ❌ Blocked |
| `false` | 1.8 ATR | Any | **0.00** | No | ❌ Blocked |
| `false` | 2.5 ATR | Any | **0.00** | No | ❌ Blocked (No sweep rejection) |
| `true` | 0.5 ATR | 1.00 | **0.00** | No | ❌ Blocked (Within normal value) |
| `true` | 1.5 ATR | 1.00 | **0.00** | No | ❌ Blocked (Below 2.0 ATR threshold) |
| `true` | 1.99 ATR | 1.00 | **0.00** | No | ❌ Blocked (Strict 2.0 ATR floor) |
| `true` | 2.00 ATR | 0.00 | **0.50** | No (at base) | ⚠️ Needs persistence / div |
| `true` | 2.00 ATR | 0.50 | **0.625** | Yes ($\ge 0.60$) | ✅ **Eligible** |
| `true` | 3.00 ATR | 0.50 | **0.750** | Yes | ✅ **Eligible** |
| `true` | 4.00 ATR | 1.00 | **1.000** | Yes | ✅ **Eligible (Maximal Conviction)** |

---

## 3. Downstream Risk Modifier Audit (Crucial Finding)

In `Regime Engine.mqh` line 183:
```mql5
case REGIME_EXHAUSTION:
   rs.preferred = HYP_MEAN_REVERSION;
   rs.risk_modifier = 0.5; // Strictly aligned with documented 0.50 countertrend risk modifier
   break;
```

### Static Call Trace & Disconnect:
1. `RegimeState rs` is produced by `EvaluateRegime(...)`.
2. `rs.preferred` is read in `Strategy Engine.mqh` via `Decide(...)`.
3. **CRITICAL GAP:** `rs.risk_modifier` is **never passed** to `RiskControllerEvaluate()` or `AccountExecutionEvaluate()`.
4. In `AMIGO.mq5` line 524, `effective_risk_pct = risk_auto.effective_risk_percent` is derived purely from account equity and daily drawdown state.
5. **Verdict:** While `rs.risk_modifier = 0.5` is correctly assigned in the regime state, the account risk controller does not consume it. Countertrend trades currently execute at the standard account-tier risk percentage rather than half-risk.

- **Status:** **GATE LOGIC VERIFIED; RISK MODIFIER INTEGRATION IS MISSING DOWNSTREAM.**
