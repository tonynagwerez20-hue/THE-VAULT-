# ALGOMIND LOG INTERPRETATION, ABBREVIATION & RATING CRITERIA REFERENCE GUIDE

This authoritative reference guide provides complete definitions, mathematical formulas, and **exact rating criteria (Pass/Fail/Quality Scale)** for every log tag, metric, decision code, and diagnostic field emitted by the **AMIGO EA (MQL5)** and the **Python External & MGLE Bridge Services**.

---

## 1. MQL5 EA LOG DIAGNOSTICS (`[AlgoMind][DIAG]`)

Log line example:
```text
[AlgoMind][DIAG] ts=2026.09.18 08:35 sym=XAUUSD tf=5 reg=7 dir=-1 fus=-0.130 flip_u=0 flip_d=0 surge=0 swp=0 cntL=0.009 cntS=0.309 mrL=0.000 mrS=0.000 sL=0.009 sS=0.309 best=0.309 mrg=0.300 th=0.42 mrg_th=0.05 act=4 rsn=REGIME_NO_TRADE
```

| Abbreviation | Full Name | Definition / Formula | Rating Criteria / Threshold Bands | Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| **`ts`** | Timestamp | Date & Time of closed bar | N/A | Execution timestamp (MT5 Server Time). |
| **`sym`** | Symbol | Traded asset | Must match `XAUUSD` or `XAUUSDm` | Primary symbol. |
| **`tf`** | Timeframe | Execution bar period | `5` (M5 Execution) | Period in minutes. |
| **`reg`** | Regime State | Market Regime ID (1–7) | **1–6: PASS (Tradeable Regimes)**<br>**7: FAIL (No-Trade / Noise)** | **Regime 1-6**: Trend/Range/Breakout (Executable)<br>**Regime 7**: High Noise / Volatility Expansion (Vetoed). |
| **`dir`** | Structure Direction | Market Structure Direction | `+1`: Bullish<br>`-1`: Bearish<br>`0`: Neutral | Higher-timeframe market structure direction. |
| **`fus`** | Delta Fusion | Normalized Order Flow ($Z_A + Z_B$) | **`<-0.25`**: Strong Bearish<br>**`-0.25 to +0.25`**: Neutral<br>**`>+0.25`**: Strong Bullish** | Combined tick delta + CLV z-scores. Measures buy vs sell pressure. |
| **`flip_u`** | Bullish Delta Flip | Order Flow Flip to Buy | **`1`: HIGH QUALITY** (Bearish to Bullish flip)<br>**`0`**: Normal | Gives +0.15 score bonus to continuation setups. |
| **`flip_d`** | Bearish Delta Flip | Order Flow Flip to Sell | **`1`: HIGH QUALITY** (Bullish to Bearish flip)<br>**`0`**: Normal | Gives +0.15 score bonus to continuation setups. |
| **`surge`** | Order Flow Surge | Extreme Order Flow Imbalance | **`1`: EXTREME MOMENTUM** ($|fus| \ge 0.60$)<br>**`0`**: Normal | Gives +0.10 score bonus for strong volume surge. |
| **`swp`** | Sweep Rejection | Liquidity Sweep & Rejection | **`1`: HIGH QUALITY REVERSION**<br>**`0`**: No sweep | Indicates stop-hunt sweep beyond key high/low followed by rejection. |
| **`cntL`** | Long Continuation | Continuation Score (Long) | **`>=0.42`: QUALIFIED**<br>**`<0.42`: WEAK** | Raw buying continuation score $[0.0, 1.0]$. |
| **`cntS`** | Short Continuation | Continuation Score (Short) | **`>=0.42`: QUALIFIED**<br>**`<0.42`: WEAK** | Raw selling continuation score $[0.0, 1.0]$. |
| **`mrL`** | Long Mean Reversion | Mean Reversion Score (Long) | **`>=0.42`: QUALIFIED**<br>**`<0.42`: WEAK** | Raw buying VWAP stretch reversion score $[0.0, 1.0]$. |
| **`mrS`** | Short Mean Reversion | Mean Reversion Score (Short) | **`>=0.42`: QUALIFIED**<br>**`<0.42`: WEAK** | Raw selling VWAP stretch reversion score $[0.0, 1.0]$. |
| **`sL`** | Overall Long Score | Combined Long Score | **`>=th`: PASS**<br>**`<th`: FAIL** | Final score for buying setup. |
| **`sS`** | Overall Short Score | Combined Short Score | **`>=th`: PASS**<br>**`<th`: FAIL** | Final score for selling setup. |
| **`best`** | Best Score | $\max(sL, sS)$ | **`>=0.42` (or input `th`): PASS**<br>**`<th`: FAIL (`SCORE_GATE`)** | Highest score across directions. Must exceed `th` to trade. |
| **`mrg`** | Score Margin | $|sL - sS|$ | **`>=0.05` (or input `mrg_th`): PASS**<br>**`<mrg_th`: FAIL (Conflicted)** | Score gap between directions. Prevents trading ambiguous setups. |
| **`th`** | Score Threshold | Minimum required score | Input setting (e.g. `0.42` or `0.35`) | Standard baseline threshold required to approve a trade. |
| **`mrg_th`** | Margin Threshold | Minimum required score margin | Input setting (e.g. `0.05`) | Minimum clarity margin required. |
| **`act`** | Action Code | Numeric Action ID (1–4) | **`1` & `2`: APPROVED**<br>**`3` & `4`: VETOED / REJECTED** | `1`=Trade, `2`=Pending, `3`=Wait, `4`=No Trade. |
| **`rsn`** | Reason String | Gate Veto Reason | **`OK`: PASS**<br>**Anything else: VETOED** | Explanation string (e.g. `OK`, `SCORE_GATE`, `REGIME_NO_TRADE`). |

---

## 2. DECISION ACTIONS & HYPOTHESES (`[DECISION]`)

Log Example:
```text
[AlgoMind][DECISION] id=1789722003033 sym=XAUUSD act=4 reg=7 hyp=0 score=0.4000 reason=REGIME_NO_TRADE
```

### Action Rating & Criteria:
* **`act=1` (`ACTION_TRADE`) — [RATING: APPROVED]**: Score $\ge th$, Margin $\ge mrg\_th$, Regime $\ne 7$, Data Quality OK.
* **`act=2` (`ACTION_PENDING`) — [RATING: APPROVED PENDING]**: Score conditions met; waiting for limit/stop touch.
* **`act=3` (`ACTION_WAIT`) — [RATING: REJECTED (LOW SCORE)]**: `best_score < th` or `margin < mrg_th`.
* **`act=4` (`ACTION_NO_TRADE`) — [RATING: REJECTED (REGIME/RISK/NEWS)]**: Vetoed by Regime 7, News Blackout, Data Quality, or Risk Cap.

### Hypothesis Rating:
* **`hyp=1` (`HYP_CONTINUATION`) — [RATING: TREND FOLLOW]**: Trade is aligned with structure and order flow momentum.
* **`hyp=2` (`HYP_MEAN_REVERSION`) — [RATING: VWAP REVERSION]**: Trade is fading an overextended ATR stretch back to VWAP.

---

## 3. POSITION SIZING & RISK RATINGS (`[SIZE_DIAG]` & `[SIZE_OVERRIDE]`)

Log Example:
```text
[AlgoMind][INFO][SIZE_OVERRIDE] MIN_LOT_OVERRIDE eq=500.00 risk_amt=2.50 min_lot_loss=3.00 dist=1.20x <= max_dist=5.00x
```

| Metric | Full Name | Rating Criteria / Threshold Bands | Rating Interpretation |
| :--- | :--- | :--- | :--- |
| **`dist`** | Risk Distortion Ratio | **`<= 1.00x`: FAITHFUL (EXCELLENT)**<br>**`1.01x - 2.00x`: MINOR DISTORTION (ACCEPTABLE)**<br>**`2.01x - 5.00x`: MODERATE DISTORTION (OVERRIDE ALLOWED)**<br>**`> 5.00x`: SEVERE DISTORTION (BLOCKED)** | $\frac{\text{min\_lot\_loss}}{\text{risk\_amt}}$. Measures how much 0.01 min lot exceeds risk budget. |
| **`max_dist`** | Max Allowed Distortion | **`5.00x` (Default Setting)** | Configured distortion ceiling. Distortions $> 5.00x$ are strictly rejected. |

---

## 4. PYTHON EXTERNAL BRIDGE RATINGS (`run_external_service.py`)

Log Example:
```text
[ExternalService] wrote ctx cftc=True opt=True src=PROXY_GLD_CBOE news=False dq=0x0000
```

| Metric | Rating Criteria / Value | Quality Rating | Interpretation |
| :--- | :--- | :--- | :--- |
| **`cftc`** | `True`: PASS<br>`False`: ABSENT | **PRIMARY (HIGH)** | Official `cftc.gov` COT report data active. |
| **`opt`** | `True`: PASS<br>`False`: ABSENT | **PROXY (MEDIUM)** | GLD options chain active (Tagged `DataQuality = PROXY`). |
| **`news`** | **`True`: BLACKOUT ACTIVE (NO-TRADE)**<br>**`False`: CLEAR (SAFE TO TRADE)** | **SAFETY FILTER** | `True` pauses all trade execution 30m before to 15m after high-impact USD releases (FOMC/CPI/NFP). |
| **`dq`** | **`0x0000`: PERFECT DATA QUALITY**<br>**`0x0002`: STALE FEED (WARN)**<br>**`0x8000`: FATAL ERROR (VETO)** | **SYSTEM HEALTH** | Bitmask health code. Non-zero codes degrade or block trading. |

---

## 5. PYTHON MGLE SHADOW RATINGS (`[AlgoMind][MGLE_SHADOW]`)

Log Example:
```text
[AlgoMind][MGLE_SHADOW] ts=2026.09.18 18:25 sym=XAUUSD reg=STRONGLY_SUPPORTIVE ry_z=-1.25 usd_z=-1.10 cftc_pct=88.5% cftc_ext=HIGH geo_idx=0.35 active_lvls=4 (SHADOW_MODE=1)
```

| Metric | Value / Range | Rating Scale / Classification | Contextual Interpretation |
| :--- | :--- | :--- | :--- |
| **`reg`** | Macro Regime | **`STRONGLY_SUPPORTIVE`**: Bullish Gold (+2)<br>**`SUPPORTIVE`**: Moderately Bullish (+1)<br>**`NEUTRAL`**: Balanced (0)<br>**`CONFLICTED`**: Mixed Signals (0)<br>**`BEARISH` / `STRONGLY_BEARISH`**: Bearish (-1/-2)** | Overall Macro Context Rating based on yields, USD, and positioning. |
| **`ry_z`** | Real Yield Robust Z | **`<-1.0`: BULLISH GOLD (Low Yields)**<br>**`-1.0 to +1.0`: NEUTRAL**<br>**`>+1.0`: BEARISH GOLD (High Yields)** | Robust Z-score of US 10Y Real Yields. |
| **`usd_z`** | USD Index Robust Z | **`<-1.0`: BULLISH GOLD (Weak USD)**<br>**`-1.0 to +1.0`: NEUTRAL**<br>**`>+1.0`: BEARISH GOLD (Strong USD)** | Robust Z-score of DXY USD Index. |
| **`cftc_pct`**| COT Percentile | **`<= 10.0%`: LOWER_EXTREME (Bullish Squeeze Risk)**<br>**`10% - 25%`: LOW**<br>**`25% - 75%`: NORMAL**<br>**`75% - 90%`: HIGH**<br>**`>= 90.0%`: UPPER_EXTREME (Bearish Squeeze Risk)** | Speculator 3-year net positioning percentile. |
| **`geo_idx`** | Geo Intensity | **`0.00 - 0.24`: LOW (Normal)**<br>**`0.25 - 0.49`: MODERATE**<br>**`0.50 - 0.79`: HIGH (Safe-Haven Flow Likely)**<br>**`0.80 - 1.00`: EXTREME (Severe Crisis)** | Multi-factor geopolitical crisis intensity index. |
| **`active_lvls`**| Macro Levels | **`>= 3`: HIGH CONFLUENCE ZONE**<br>**`1 - 2`: MODERATE**<br>**`0`: NO NEARBY MACRO LEVELS** | Count of ATR-normalized serious macro/structural levels nearby. |
