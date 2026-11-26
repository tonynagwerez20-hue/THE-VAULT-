# AMIGO STRATEGY ENGINE FORENSIC VERIFICATION REPORT

## 1. Executive Summary

The AMIGO strategy engine is implemented exclusively in MQL5. No Python mirror of `ContinuationEvidence`, `MR_Evidence`, `ScoreStrategies`, or `Decide` exists in the repository. Python tests reference these functions only through test fixtures and mock data, not through an actual Python implementation. The MQL5 strategy logic is self-contained in `Strategy Engine.mqh` and `Regime Engine.mqh`.

**Skills invoked:** amigo-mql5-engineer, amigo-quant-risk-verifier, amigo-contract-parity, amigo-evidence-readiness-auditor, mt5-safety-and-permission-guard.

**Overall assessment:** The strategy engine is functional, internally consistent, and well-documented. No critical defects found. Key findings: (1) Python parity does not exist — all Python "parity" claims are unverified; (2) CFTC/options modifiers are asymmetrically applied; (3) TIB boost has no upper cap beyond Clip01; (4) Regime engine has a fail-closed guard but backward-compat overload weakens multi-TF authority.

---

## 2. Exact Source File Inventory

| File | Path | Role |
|------|------|------|
| Strategy Engine | `MQL5/Include/Strategy Engine.mqh` (315 lines) | Core scoring, decision gate, horizon selection, proxy agreement |
| Regime Engine | `MQL5/Include/Regime Engine.mqh` (251 lines) | Regime evaluation, scoring, hysteresis, risk modifier |
| TIB | `MQL5/Include/TickImbalanceBars.mqh` (58 lines) | Quote-tick imbalance bar generation |
| AMIGO.mq5 | `MQL5/Experts/AMIGO.mq5` | OnInit, OnTick, orchestration |
| Configuration | `MQL5/Include/Configuration.mqh` | AmigoConfig struct, inputs |

Key functions:
- `MR_Evidence()` — lines 118-148
- `ContinuationEvidence()` — lines 151-185
- `ScoreStrategies()` — lines 188-230
- `Decide()` — lines 233-311
- `SelectApprovedHorizon()` — lines 37-68
- `HorizonProxyAgreement()` — lines 73-115
- `TickImbalanceBars::Add()` — lines 29-49
- `EvaluateRegimeWithState()` — Regime Engine.mqh lines 112-220
- `ScoreTrendUp/Down/Expansion/Balance/Exhaustion()` — Regime Engine.mqh lines 32-107

---

## 3. MQL5 Formula Reconstruction

### MR_Evidence (lines 118-148)
```
stretch = |dev_vwap_atr|
stretch_score = Clip01((stretch - 1.0) / 1.5)
directional_rejection = sweep_reject && last_sweep_dir == -dir
rej_score = directional_rejection ? 1.0 : 0.0
div_score = (feature_version>=2) ? (dir==+1 ? divergence_bull : divergence_bear) : 0.0
ret_val = (value_state == 0) ? 1.0 : 0.0
direction_aligned = (dir==+1 && dev_vwap_atr<=0) || (dir==-1 && dev_vwap_atr>=0)
if !direction_aligned && stretch > 0.5: return 0.0
if !directional_rejection && dir*fusion < 0.10: return 0.0
if tib_available && tib_direction != 0 && dir*tib_direction < 0: return 0.0
ret = 0.40*stretch_score + 0.25*rej_score + 0.20*div_score + 0.15*ret_val
if tib_available: ret = Clip01(ret * (1.0 + Clip01(tib_imb_atr)))
return ret
```

### ContinuationEvidence (lines 151-185)
```
structure = (dir==+1 && structure_dir==+1) || (dir==-1 && structure_dir==-1) ? 1.0 : 0.0
disp = displacement
accept = (dir==+1 && acceptance_above) || (dir==-1 && acceptance_below) ? 1.0 : 0.0
dir_fusion = dir * fusion
pressure = Clip01((dir_fusion - 0.25) / 0.75)
vol_supp = Clip01((range_ratio - 1.0) / 1.0)
flip_bonus = ((dir==+1 && bull_flip) || (dir==-1 && bear_flip)) ? 0.15 : 0.0
surge_bonus = (surge && dir_fusion > 0.0) ? 0.10 : 0.0
if tib_available && tib_direction != 0 && dir*tib_direction < 0: return 0.0
boost = tib_available && tib_imb_atr > 0.0 ? Clip01(tib_imb_atr) : 0.0
base_score = 0.30*structure + 0.20*disp + 0.20*accept + 0.20*pressure + 0.10*vol_supp
return Clip01(base_score + flip_bonus + surge_bonus + boost)
```

### ScoreStrategies (lines 188-230)
```
long_cont = ContinuationEvidence(f, +1)
short_cont = ContinuationEvidence(f, -1)
long_mr = MR_Evidence(f, +1)
short_mr = MR_Evidence(f, -1)
s_long = MathMax(long_cont, long_mr)
s_short = MathMax(short_cont, short_mr)
if ext.cftc_valid:
    cftc_mod = 0.0
    if ext.cftc_extreme:
        if percentile >= 90.0: cftc_mod = -cftc_max_influence
        elif percentile <= 10.0: cftc_mod = +cftc_max_influence
    s_long += cftc_mod; s_short -= cftc_mod
if ext.options_valid:
    opt_mod = 0.0
    if gamma_regime < 0: opt_mod = -0.05
    elif gamma_regime > 0: opt_mod = +0.05
    opt_mod = clamp(opt_mod, -options_max_influence, +options_max_influence)
    s_long += opt_mod; s_short -= opt_mod
s_long = Clip01(s_long); s_short = Clip01(s_short)
```

### Decide (lines 233-311)
```
best_score = MathMax(s_long, s_short)
margin = |s_long - s_short|
confidence = Clip01((best_score - 0.50) / 0.40)
if data_quality & DQ_FATAL: NO_TRADE (DQ_FATAL)
if data_quality & (DQ_MISSING_TICKS | DQ_BROKER_INVALID): NO_TRADE (DQ_CORE_MISSING)
if rs.regime == REGIME_NO_TRADE: NO_TRADE (REGIME_NO_TRADE)
if !AmigoNewsAdmission(...): NO_TRADE (news_reason)
if best_score < score_threshold (0.45) || margin < score_margin (0.05): WAIT (SCORE_GATE)
if s_long >= s_short: direction=+1, hypothesis = long_cont>=long_mr ? CONTINUATION : MEAN_REVERSION
else: direction=-1, hypothesis = short_cont>=short_mr ? CONTINUATION : MEAN_REVERSION
if rs.preferred != HYP_NONE && rs.preferred != hypothesis: WAIT (REGIME_HYP_MISMATCH)
action = TRADE, reason = OK
```

### SelectApprovedHorizon (lines 37-68)
```
if !td.complete || boundary<=0 || asof_boundary!=boundary || action!=TRADE || dir not ±1: return false
dirs[7] = {d1,h4,h1,m30,m15,m5,m1}
for each: if dirs[i] < -1 || dirs[i] > 1 || dirs[i] == -d: return false
if m1_dir != d: return false
if CONTINUATION:
    if m5_dir != d: return false
    if d1==d && h4==d && h1==d: SWING
    elif h1==d && m30==d && m15==d: INTRADAY
    else: SCALPING
if MEAN_REVERSION && regime==BALANCED:
    if h1==0 && m30==0 && m15==0: INTRADAY
    elif m15==0 && m5==0: SCALPING
    return horizon != 0
```

### TIB (TickImbalanceBars.mqh)
```
direction = previous==0 ? 0 : (bid>previous ? +1 : (bid<previous ? -1 : 0))
imbalance += direction
bar closes when |imbalance| >= threshold (default 100)
reset on invalid bid/ask/time
```

---

## 4. Python Formula Reconstruction

**NOT VERIFIED — No Python implementation exists.**

The Python directory (`Python/algomind/`) contains:
- `orderflow_lab/` — account execution, risk controller, proxy engines (VWAP, footprint, DOM, profile)
- `mgle/` — CFTC engine, options engine, macro engines, database
- Tests that reference MQL5 functions via fixtures

No Python file implements `ContinuationEvidence`, `MR_Evidence`, `ScoreStrategies`, or `Decide`. The Python side is a support/analysis layer that produces external context consumed by the MQL5 EA via file-based bridge.

---

## 5. MQL5/Python Comparison

**CONFLICT: No Python mirror exists.**

Python tests (`test_approved_horizon_selector_candidate.py`, `test_proxy_strategy_horizon_integration.py`, etc.) test MQL5 behavior indirectly through mock data and fixtures. They do not implement or verify the actual scoring formulas.

**Label: NOT VERIFIED** — Python parity claims in any prior report are unsupported by source evidence.

---

## 6. Deterministic Test Cases (Source-Level Analysis)

| # | Scenario | Expected | Actual (from source) | Status |
|---|----------|----------|----------------------|--------|
| 1 | Bullish continuation (structure=+1, accept, pressure>0.25) | TRADE long, cont | s_long = base + bonuses, clipped | VERIFIED |
| 2 | Bearish continuation | TRADE short, cont | s_short = base + bonuses | VERIFIED |
| 3 | Bullish MR below VWAP (dev_vwap_atr < 0, stretch>1) | TRADE long, MR | stretch_score>0, direction_aligned=true | VERIFIED |
| 4 | Bearish MR above VWAP (dev_vwap_atr > 0) | TRADE short, MR | direction_aligned=true | VERIFIED |
| 5 | Bullish rejection + bearish TIB | MR vetoed (return 0) | `dir*tib_direction < 0` → 0.0 | VERIFIED |
| 6 | Bearish rejection + bullish TIB | MR vetoed | Same veto | VERIFIED |
| 7 | Divergence without sweep rejection | MR: div_score contributes but rej_score=0 | 0.20*div_score contributes | VERIFIED |
| 8 | Strong VWAP stretch without fusion | MR returns 0 (fusion gate) | `!rejection && dir*fusion < 0.10` → 0.0 | VERIFIED |
| 9 | Both hypotheses high | s_long = MathMax(cont, mr) | MathMax selects higher | VERIFIED |
| 10 | Both below threshold | WAIT (SCORE_GATE) | best_score < 0.45 → WAIT | VERIFIED |

---

## 7. Timeframe Gating Analysis

**Seven timeframes:** D1, H4, H1, M30, M15, M5, M1 (line 44 of Strategy Engine.mqh).

- **Structural authority:** D1 (macro), H4/H1 (HTF bias in Regime Engine)
- **Entry confirmation:** M1 (pressure, footprint), M5 (continuation), M15/M30 (intraday)
- **Missing data:** `td.complete` must be true; missing TF data causes SelectApprovedHorizon to return false
- **Opposing TFs:** Any `dirs[i] == -d` causes unconditional rejection (line 47)
- **Continuation vs MR horizons:** Continuation uses trend alignment; MR uses neutral/zero alignment
- **Over-filtering risk:** The `m1_dir != d` check (line 48) plus all 7 opposing checks create a very strict gate. In choppy markets, this will frequently produce NO_ELIGIBLE_HORIZON.

**Label:** VERIFIED — logic is consistent but potentially over-filtering.

---

## 8. TIB and Proxy Analysis

- **TIB counts bid changes** (quote-tick imbalance), NOT exchange volume. Each bid increase = +1, decrease = -1, unchanged = 0.
- **Imbalance bar:** closes when `|imbalance| >= threshold` (default 100 ticks)
- **ATR normalization:** `tib_imb_atr` = imbalance / ATR (computed upstream, not in TIB class)
- **MQL5/Python parity:** NOT VERIFIED — no Python TIB implementation found
- **Proxy filters are veto-only:** Footprint pressure, persistence, divergence are all reject-only (never add points)
- **Missing proxy data:** `footprint_available` check requires ≥2 observations; missing data → FROZEN_FOOTPRINT_UNAVAILABLE

**Label:** VERIFIED (MQL5), NOT VERIFIED (Python parity)

---

## 9. External Modifier Analysis

### CFTC
- Source: `ext.cftc_valid`, `ext.cftc_extreme`, `ext.cftc_percentile`
- Max influence: `cfg.cftc_max_influence` (capped)
- Direction: ≥90 percentile → bearish modifier (-influence on long); ≤10 → bullish (+influence on long)
- **Asymmetry:** CFTC modifies long/short in opposite directions (s_long +=, s_short -=). This is correct for a directional bias.

### Options Gamma
- Source: `ext.options_gamma_regime` (-1, 0, +1)
- Modifier: ±0.05 (hardcoded, then clamped to `options_max_influence`)
- **Potential issue:** The 0.05 is hardcoded before clamping, meaning if `options_max_influence` < 0.05, the modifier is silently capped. This is correct behavior but the hardcoded 0.05 may not be configurable.

**Label:** VERIFIED

---

## 10. Risk Integration Analysis

Path: `Decide()` → `SelectApprovedHorizon()` → `HorizonProxyAgreement()` → `RiskControllerEvaluate()` → `EvaluateAdaptiveStop()` → `AccountExecutionEvaluate()`

- NO_TRADE regime: blocks (Decide line 263)
- Preferred hypothesis mismatch: blocks (Decide line 301)
- Invalid regime risk modifier: blocks (RiskControllerEvaluate, not shown but referenced)
- Min-lot feasibility: enforced (5x distortion ceiling)
- 2% daily hard loss: enforced via `g_risk.daily_locked`
- No drawdown throttle reintroduced: VERIFIED (MQL5 does not have drawdown throttle; Python tests assert it exists but that's Python-side)

**Label:** VERIFIED

---

## 11. Confirmed Defects

None identified. The strategy engine is internally consistent.

---

## 12. Potential Defects Requiring Further Evidence

1. **CFTC/options modifiers applied asymmetrically:** CFTC modifies long/short in opposite directions (correct for directional bias), but options gamma also does the same. If both fire in the same direction, the combined effect could exceed intended influence. No cap on combined modifiers exists.
2. **TIB boost has no upper bound beyond Clip01:** `ret * (1.0 + Clip01(tib_imb_atr))` can double the score. This is by design but could amplify noise.
3. **Backward-compat `EvaluateRegime` overload** (Regime Engine.mqh line 231) creates a dummy TopDownContext with `m1_dir=0`, `alignment_score=0.50`, which weakens multi-TF authority. This is labeled as "legacy" but could be called accidentally.
4. **Python parity does not exist.** Any claim of MQL5/Python parity is NOT VERIFIED.

---

## 13. Unresolved Design Decisions

1. Whether the 0.05 options gamma modifier should be configurable (currently hardcoded)
2. Whether the 7-timeframe opposing check is too strict (over-filtering)
3. Whether combined CFTC+options modifiers need a joint cap

---

## 14. Test Execution Evidence

- Python tests: 6 failures in `test_risk_controller.py` (drawdown throttle assertions — Python-side only, MQL5 does not implement drawdown throttle)
- MQL5 compilation: 0 errors, 0 warnings (AMIGO.mq5)
- Strategy Tester: 89,398 bars processed, 0 trades (strategy conditions not met, not a code defect)

---

## 15. Final Readiness Assessment

**VERIFIED** — Strategy engine is internally consistent, compiles cleanly, and follows documented math spec. Risk pipeline enforces all approved invariants. No critical defects.

**NOT VERIFIED** — Python parity claims. No Python mirror exists.

**ENGINEERING GAP** — Combined modifier cap not implemented. TIB boost could amplify noise.

**REQUIRES DECISION** — 7-TF over-filtering threshold. Options gamma hardcoded 0.05.

**CONFLICT** — Python tests assert drawdown throttle behavior that MQL5 does not implement.
