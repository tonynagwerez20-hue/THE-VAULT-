# ALGOMIND LOG INTERPRETATION & ABBREVIATION REFERENCE GUIDE

This authoritative reference guide provides complete definitions and mathematical formulas for every log tag, metric, decision code, and diagnostic field emitted by the **AMIGO EA (MQL5)** and the **Python External & MGLE Bridge Services**.

---

## 1. MQL5 EA LOG DIAGNOSTICS (`[AlgoMind][DIAG]`)

Log line example:
```text
[AlgoMind][DIAG] ts=2026.09.18 08:35 sym=XAUUSD tf=5 reg=7 dir=-1 fus=-0.130 flip_u=0 flip_d=0 surge=0 swp=0 cntL=0.009 cntS=0.309 mrL=0.000 mrS=0.000 sL=0.009 sS=0.309 best=0.309 mrg=0.300 th=0.42 mrg_th=0.05 act=4 rsn=REGIME_NO_TRADE
```

| Abbreviation | Full Name | Definition / Formula | Interpretation |
| :--- | :--- | :--- | :--- |
| **`ts`** | Timestamp | Date & Time of closed bar | Execution timestamp (MT5 Server Time). |
| **`sym`** | Symbol | Traded asset | Primary symbol (e.g. `XAUUSD`). |
| **`tf`** | Timeframe | Execution bar period | Period in minutes (`5` = M5 time-frame). |
| **`reg`** | Regime State | Market Regime ID (1–7) | Classified market regime (e.g. `reg=3` Trend, `reg=7` Noise/No-Trade). |
| **`dir`** | Structure Direction | Market Structure Direction | `+1` = Bullish, `-1` = Bearish, `0` = Neutral. |
| **`fus`** | Delta Fusion | Normalized Order Flow ($Z_A + Z_B$) | Scale $[-1.0, +1.0]$. Positive = buying pressure, Negative = selling pressure. |
| **`flip_u`** | Bullish Delta Flip | Order Flow Flip to Buy | `1` = Transitioned from Bearish ($\le -0.25$) to Bullish ($\ge +0.25$). `0` = No flip. |
| **`flip_d`** | Bearish Delta Flip | Order Flow Flip to Sell | `1` = Transitioned from Bullish ($\ge +0.25$) to Bearish ($\le -0.25$). `0` = No flip. |
| **`surge`** | Order Flow Surge | Extreme Order Flow Imbalance | `1` = $|fus| \ge 0.60$ (High momentum surge). `0` = Normal volume. |
| **`swp`** | Sweep Rejection | Liquidity Sweep & Rejection | `1` = Price swept liquidity beyond key high/low & rejected. `0` = No sweep. |
| **`cntL`** | Long Continuation | Continuation Score (Long) | Raw score $[0.0, 1.0]$ for buying trend continuation. |
| **`cntS`** | Short Continuation | Continuation Score (Short) | Raw score $[0.0, 1.0]$ for selling trend continuation. |
| **`mrL`** | Long Mean Reversion | Mean Reversion Score (Long) | Raw score $[0.0, 1.0]$ for buying overextended price dip to VWAP. |
| **`mrS`** | Short Mean Reversion | Mean Reversion Score (Short) | Raw score $[0.0, 1.0]$ for selling overextended price rally to VWAP. |
| **`sL`** | Overall Long Score | $\max(cntL, mrL) + \text{modifiers}$ | Combined score for Long direction. |
| **`sS`** | Overall Short Score | $\max(cntS, mrS) - \text{modifiers}$ | Combined score for Short direction. |
| **`best`** | Best Score | $\max(sL, sS)$ | Highest strategy score among buying & selling. |
| **`mrg`** | Score Margin | $|sL - sS|$ | Absolute score difference between buying & selling setups. |
| **`th`** | Score Threshold | Minimum required score | EA input threshold (e.g. `0.42` or `0.35`). Must have `best >= th`. |
| **`mrg_th`** | Score Margin Threshold | Minimum required score margin | Required clarity gap between directions (e.g. `0.05`). |
| **`act`** | Action Code | Numeric Action ID (1–4) | `1` = Trade, `2` = Pending, `3` = Wait, `4` = No Trade. |
| **`rsn`** | Reason String | Gate Veto Reason | Primary reason for action decision (e.g. `OK`, `SCORE_GATE`, `REGIME_NO_TRADE`). |

---

## 2. DECISION ACTIONS & HYPOTHESES (`[DECISION]`)

Log line example:
```text
[AlgoMind][DECISION] id=1789722003033 sym=XAUUSD act=4 reg=7 hyp=0 score=0.4000 reason=REGIME_NO_TRADE
```

### Action Codes (`act`):
* **`act=1` (`ACTION_TRADE`)**: Approved! EA initiates order execution.
* **`act=2` (`ACTION_PENDING`)**: Approved pending limit/stop placement.
* **`act=3` (`ACTION_WAIT`)**: Scores didn't reach threshold or margin requirements (`SCORE_GATE`).
* **`act=4` (`ACTION_NO_TRADE`)**: Trade vetoed by Regime, Data Quality, News, or Risk.

### Hypothesis Codes (`hyp`):
* **`hyp=0` (`HYP_NONE`)**: No qualified hypothesis.
* **`hyp=1` (`HYP_CONTINUATION`)**: Trend continuation setup.
* **`hyp=2` (`HYP_MEAN_REVERSION`)**: VWAP mean-reversion stretch setup.

### Common Rejection Reasons (`reason` / `rsn`):
* **`OK`**: All conditions satisfied.
* **`SCORE_GATE`**: `best_score < score_threshold` or `margin < score_margin`.
* **`REGIME_NO_TRADE`**: Market classified in Regime 7 (noisy/choppy conditions).
* **`REGIME_HYP_MISMATCH`**: Strategy setup conflicts with current market regime direction.
* **`MIN_LOT_EXCEEDS_RISK`**: Minimum 0.01 lot loss exceeds configured risk budget (e.g. $2.50).
* **`NEWS_FILTER`**: Trading paused during high-impact news blackout window (e.g., FOMC/CPI).
* **`DQ_FATAL` / `DQ_CORE_MISSING`**: Data quality flaw (stale feeds, missing ticks).

---

## 3. POSITION SIZING & RISK LOGS (`[SIZE_DIAG]` & `[SIZE_OVERRIDE]`)

Log line example:
```text
[AlgoMind][INFO][SIZE_OVERRIDE] MIN_LOT_OVERRIDE eq=500.00 risk_amt=2.50 min_lot_loss=3.00 dist=1.20x <= max_dist=5.00x
```

| Abbreviation | Full Name | Definition / Formula |
| :--- | :--- | :--- |
| **`eq`** | Account Equity | Current account equity in USD. |
| **`risk_amt`** | Risk Amount | Configured dollar risk budget ($Equity \times \text{Risk\%}$). |
| **`stop_dist`** | Stop Distance | Distance between Entry and Stop Loss in price points. |
| **`tick_sz`** | Tick Size | Minimum price movement step (e.g. `0.001` or `0.01`). |
| **`tick_val`** | Tick Value | Monetary value per tick for 1.00 lot (e.g. `$0.10`). |
| **`loss_per_lot`** | Dollar Loss per Lot | Monetary loss for 1.00 lot hit at SL ($\text{stop\_dist} \times \text{Contract Size}$). |
| **`min_lot_loss`** | Minimum Lot Loss | Dollar loss for 0.01 minimum lot ($\text{loss\_per\_lot} \times 0.01$). |
| **`min_vol`** | Minimum Volume | Smallest executable lot size allowed by broker (`0.01`). |
| **`dist`** | Risk Distortion Ratio | Ratio of minimum lot loss to intended risk budget ($\frac{\text{min\_lot\_loss}}{\text{risk\_amt}}$). |
| **`max_dist`** | Max Allowed Distortion | User-configured distortion multiplier cap (e.g. `5.00x`). |

---

## 4. PYTHON EXTERNAL BRIDGE LOGS (`run_external_service.py`)

Log line example:
```text
[ExternalService] wrote ctx cftc=True opt=True src=PROXY_GLD_CBOE news=False dq=0x0000
```

| Abbreviation | Full Name | Meaning |
| :--- | :--- | :--- |
| **`cftc`** | CFTC Context Valid | `True` if official `cftc.gov` COT report data is active. |
| **`opt`** | Options Context Valid | `True` if GLD options chain data is active. |
| **`src`** | Options Data Source | Sourced pipeline (`PROXY_GLD_CBOE` or `PROXY_YFINANCE`). |
| **`news`** | Active News Window | `True` if high-impact USD news blackout is active (trading paused). |
| **`dq`** | Data Quality Bitmask | Bitmask hex code (`0x0000` = OK, `0x0002` = Stale, `0x0010` = Absent). |

---

## 5. PYTHON MGLE SHADOW LOGS (`[AlgoMind][MGLE_SHADOW]`)

Log line example:
```text
[AlgoMind][MGLE_SHADOW] ts=2026.09.18 18:25 sym=XAUUSD reg=STRONGLY_SUPPORTIVE ry_z=-1.25 usd_z=-1.10 cftc_pct=88.5% cftc_ext=HIGH geo_idx=0.35 active_lvls=4 (SHADOW_MODE=1)
```

| Abbreviation | Full Name | Meaning / Scale |
| :--- | :--- | :--- |
| **`reg`** | Macro Regime Label | `STRONGLY_SUPPORTIVE`, `SUPPORTIVE`, `NEUTRAL`, `CONFLICTED`, `BEARISH`, `STRONGLY_BEARISH`. |
| **`ry_z`** | Real Yield Robust Z-Score | Robust MAD-scaled Z-score of US 10Y Real Yields (Negative = Bullish Gold). |
| **`usd_z`** | USD Index Robust Z-Score | Robust MAD-scaled Z-score of DXY Index (Negative = Bullish Gold). |
| **`cftc_pct`** | CFTC Managed Money Percentile | 3-Year percentile rank of speculator net long positions ($0.0\% - 100.0\%$). |
| **`cftc_ext`** | CFTC Extreme State | `LOWER_EXTREME` ($\le 10\%$), `LOW`, `NORMAL`, `HIGH`, `UPPER_EXTREME` ($\ge 90\%$). |
| **`geo_idx`** | Geopolitical Intensity Index | Normalized index $[0.0, 1.0]$ measuring news velocity, severity & persistence. |
| **`active_lvls`** | Active Macro Levels Count | Number of active serious ATR-normalized Macro Levels detected. |
| **`SHADOW_MODE=1`**| Shadow Execution Flag | `1` = Operating in diagnostic logging mode (0 impact on execution). |
