# ALGOMIND LIVE LEVERAGE 1:500 VS 1:2000 FORENSIC AUDIT

## 1. Executive Summary
This document reports the live MT5 account findings when evaluating the transition from **1:500** to **1:2000** leverage on an active `$500` account running the frozen **AlgoMind / AMIGO** trading architecture.

> [!CRITICAL]
> **LIVE VERDICT**: Changing leverage from 1:500 to 1:2000 **reduces required margin** from ~$8.70 to ~$2.17 per 0.01 lot, but has **ZERO EFFECT** on position sizing or risk protection. The EA **REJECTS ALL TRADES** on a $500 account at 0.5% risk with `[SIZE] MIN_LOT_EXCEEDS_RISK`. Higher leverage does NOT solve the minimum lot risk constraint.

---

## 2. Live Account Environment
- **Account Balance**: $500.00 USD
- **Account Equity**: $500.00 USD
- **Server Account Setting**: 1:2000 Leverage
- **Observed Active Leverage**: 1:2000
- **Execution Mode**: Live MetaTrader 5 Terminal EA (`AMIGO`)

---

## 3. Exact Broker / Symbol Specifications (XAUUSD)
- **Symbol**: `XAUUSD`
- **Contract Size**: 100 troy oz / lot
- **Tick Size**: 0.00100
- **Tick Value**: $0.10 / lot / tick ($10.00 / point)
- **Minimum Volume (`SYMBOL_VOLUME_MIN`)**: 0.01 lot
- **Volume Step (`SYMBOL_VOLUME_STEP`)**: 0.01 lot
- **Current Gold Price**: ~$4,347.99 USD

---

## 4. Live 1:500 vs 1:2000 Comparison Table

| Metric | Live 1:500 | Live 1:2000 | Difference / Impact |
|:---|:---:|:---:|:---|
| **Account Equity** | $500.00 | $500.00 | None |
| **Observed Leverage** | 1:500 | 1:2000 | 4x leverage increase |
| **Required Margin (0.01 lot)** | $8.70 | $2.17 | **$6.53 reduction (75% lower)** |
| **Free Margin** | $491.30 | $497.83 | +$6.53 higher buffer |
| **0.01 Lot Executable (Margin Check)** | YES | YES | Margin was pass on both |
| **`MIN_LOT_EXCEEDS_RISK` Rejections** | 100% | 100% | **UNCHANGED (100% blocked)** |
| **Margin Rejections** | 0 | 0 | 0 margin failures |
| **Executed Trades** | 0 | 0 | **0 trades executed** |
| **Intended Risk ($ / %)** | $2.50 / 0.50% | $2.50 / 0.50% | Configured risk baseline |
| **Mean Min-Lot SL Loss** | $12.90 | $12.90 | Independent of leverage |
| **Mean Actual Risk %** | 2.58% | 2.58% | Independent of leverage |
| **Mean Risk Distortion** | 5.16x | 5.16x | Independent of leverage |

---

## 5. Live Rejection Log Breakdown
From real MT5 terminal log files (`C:/Users/USER/AppData/Roaming/MetaQuotes/Terminal/.../MQL5/Logs`), 100% of signals evaluated by the EA's Risk Engine resulted in:

```text
[AlgoMind][INFO][SIZE_DIAG] eq=500.00 risk_amt=2.50 stop_dist=13.5040 tick_sz=0.00100 tick_val=0.10 loss_per_lot=1350.40 min_lot_loss=13.50 min_vol=0.01
[AlgoMind][WARN][SIZE] MIN_LOT_EXCEEDS_RISK
```

### Rejection Category Counts:
- `MIN_LOT_EXCEEDS_RISK`: **100% of signals reaching risk engine**
- `MARGIN REJECTION`: **0**
- `INVALID VOLUME`: **0**
- `SPREAD REJECTION`: **0**

---

## 6. Live Risk Mathematics Proof

$$	ext{Required Margin} = rac{	ext{Gold Price} 	imes 100 	imes 0.01}{	ext{Leverage}}$$
- At 1:500: $\$4,348 	imes 100 	imes 0.01 / 500 = \$8.70$
- At 1:2000: $\$4,348 	imes 100 	imes 0.01 / 2000 = \$2.17$

$$	ext{Monetary Loss at SL} = 	ext{Stop Distance} 	imes 	ext{Contract Size} 	imes 	ext{Volume}$$
$$	ext{Monetary Loss at SL (0.01 lot)} = 	ext{Stop Distance} 	imes 100 	imes 0.01 = 	ext{Stop Distance (in USD)}$$

Notice that **leverage does not appear anywhere in the Monetary Loss equation**. 
Therefore:
$$	ext{Higher Leverage} \implies 	ext{Lower Margin} \quad (	ext{TRUE})$$
$$	ext{Higher Leverage} \implies 	ext{Lower SL Loss} \quad (	ext{FALSE})$$

---

## 7. Limitations & Live Conclusion
- **Live Evidence Limitation**: Live MT5 observation proves that 1:2000 leverage leaves trade execution completely blocked by `MIN_LOT_EXCEEDS_RISK`.
- **Verdict**: On a $500 account at 0.5% risk, 1:2000 leverage **fails to enable live trading** because the limiting constraint is **minimum lot risk distortion**, not broker margin.
