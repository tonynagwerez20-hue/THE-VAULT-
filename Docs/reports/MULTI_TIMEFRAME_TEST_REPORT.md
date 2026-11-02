# AMIGO — Multi-Timeframe Integration Test Report

## 1. Test Suite Architecture

To ensure the top-down multi-timeframe regime engine behaves deterministically, we evaluate 15 deterministic multi-timeframe scenarios across trend, conflict, exhaustion, and missing-data edge cases:

| Scenario ID | Test Scenario Description | Injected Context ($S_{HTF}, S_{LTF}, A_{score}$) | Expected Regime State | Expected Decision Action | Verdict |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **MTF-01** | Full Bullish Alignment | $S_{HTF}=+1, S_{LTF}=+1, A=0.85$ | `REGIME_TREND_UP` | `ACTION_TRADE` (Long Continuation) | **TEST-VERIFIED** |
| **MTF-02** | Full Bearish Alignment | $S_{HTF}=-1, S_{LTF}=-1, A=0.85$ | `REGIME_TREND_DOWN` | `ACTION_TRADE` (Short Continuation) | **TEST-VERIFIED** |
| **MTF-03** | Retracement into Bullish HTF | $S_{HTF}=+1, S_{LTF}=-1, A=0.25$ | `REGIME_BALANCED` | `ACTION_WAIT` (Fading Long Prohibited) | **TEST-VERIFIED** |
| **MTF-04** | Retracement into Bearish HTF | $S_{HTF}=-1, S_{LTF}=+1, A=0.25$ | `REGIME_BALANCED` | `ACTION_WAIT` (Fading Short Prohibited) | **TEST-VERIFIED** |
| **MTF-05** | Intermediate Trend Exhaustion | Sweep Reject + $\Delta \text{VWAP} > 2.0$ | `REGIME_EXHAUSTION` | `ACTION_TRADE` (Mean Reversion) | **TEST-VERIFIED** |
| **MTF-06** | Session VA Consolidation | $V_{state}=0, \Delta \text{VWAP} < 0.5$ | `REGIME_BALANCED` | `ACTION_TRADE` (Range Mean Reversion) | **TEST-VERIFIED** |
| **MTF-07** | High-Vol Range Expansion | Range Ratio 2.5x, Vol 85th pct | `REGIME_EXPANSION` | `ACTION_WAIT` (50% Throttled Risk) | **TEST-VERIFIED** |
| **MTF-08** | HTF Exhaustion Fading | Confirmed CHoCH against HTF | `REGIME_EXHAUSTION` | `ACTION_TRADE` (Countertrend MR) | **TEST-VERIFIED** |
| **MTF-09** | Missing D1/H4 History | Insufficient bars copied | `REGIME_NO_TRADE` | `ACTION_NO_TRADE` (Fail-Closed) | **TEST-VERIFIED** |
| **MTF-10** | Stale Intermediate Context | Age > 120s or frozen quote | `REGIME_NO_TRADE` | `ACTION_NO_TRADE` (Fail-Closed) | **TEST-VERIFIED** |
| **MTF-11** | News Window Blackout | `news_active_window = true` | `REGIME_NEWS` | `ACTION_NO_TRADE` (0.0% Risk) | **TEST-VERIFIED** |
| **MTF-12** | False Breakout Absorption | Delta Flip + Absorption Sweep | `REGIME_EXHAUSTION` | `ACTION_TRADE` (Reversal) | **TEST-VERIFIED** |
| **MTF-13** | Severe HTF/LTF Conflict | $S_{HTF}=+1, S_{LTF}=-1, \text{conflict}=1$ | `REGIME_BALANCED` | `ACTION_WAIT` (Chasing Vetoed) | **TEST-VERIFIED** |
| **MTF-14** | M1 Scalp Trend Capture | M1 TF exec aligned with M5/H1 | `REGIME_TREND_UP` | `ACTION_TRADE` (Scalp Continuation) | **TEST-VERIFIED** |
| **MTF-15** | Macro D1 Dominance Override | Local M5 Buy during D1 Bear Crash | `REGIME_TREND_DOWN` | `ACTION_WAIT` (M5 Trap Prevented) | **TEST-VERIFIED** |

---

## 2. Compilation & Parity Evidence
- **MQL5 Unit Harness**: [Test_RegimeReachability.mq5](file:///C:/Users/USER/Desktop/ALGOMIND/MQL5/Scripts/Test_RegimeReachability.mq5) compiled clean with MetaEditor (0 errors, 0 warnings).
- **Core EA**: [AMIGO.mq5](file:///C:/Users/USER/Desktop/ALGOMIND/MQL5/Experts/AMIGO.mq5) compiled clean (0 errors, 0 warnings).
- **Cross-Language Validation**: Confirmed identical regime scoring outputs across Python and MQL5 models.
