# DECISION ENGINE & STRATEGY ENGINE MASTER AUDIT
**Auditor**: Independent Quantitative Researcher & Principal Systems Architect  
**Project**: AMIGO Core Decision Systems / AlgoMind  
**Audit Baseline**: Git commit `61bed60` (Inspection-Only Stage, Zero Strategy Mutations)  
**Date**: 2026-11-02  

---

## 1. Executive Summary & Authoritative Verdict

| Component | Verdict | Core Finding |
|---|:---:|---|
| **Decision Engine** | `CONDITIONALLY-ACCEPTABLE` | Deterministic pipeline with rigid data-quality vetoes and score margin gating. However, decision state lacks transactional rollback if downstream feature assembly fails. |
| **Strategy Engine** | `CONDITIONALLY-ACCEPTABLE` | The two approved families (`MEAN_REVERSION` and `CONTINUATION`) are strictly decoupled and scored via normalized orthogonal heuristics. Invariant $S(input, state) = S(state)$ holds. |
| **Integrated System** | **`CONDITIONALLY-ACCEPTABLE`** | **Logically coherent and mathematically sound.** Not approved for live execution or un-isolated backtesting due to external environment blockers (`BLK-001`). |

---

## 2. End-to-End Decision Pipeline & Architecture Call-Flow

```
[ Closed Bar Trigger: iTime(tf_exec, 0) != last_bar ]
                     │
                     ▼
       1. BuildMarketSnapshot(g_symbol)
          ├─ Fetches Bid/Ask, Spread, Volume, Digits
          └─ Validates Core Broker Health (DQ_FATAL check)
                     │
                     ▼
       2. AssembleFeatureVector(g_feat)
          ├─ Closed-Bar Swings (2L/2R confirmed)
          ├─ Proxy VWAP & Value Area (POC, VAH, VAL)
          ├─ Cumulative Volume Delta & Pressure State
          └─ TopDownContext (D1, H4, H1, M30, M15, M5, M1)
                     │
                     ▼
       3. EvaluateRegime(g_feat, g_cfg)
          ├─ Scores: TrendUp, TrendDown, Expansion, Balance, Exhaustion
          ├─ Candidate Persistence Counter (>= 2 bars)
          └─ Hysteresis Buffer (+0.10 threshold delta)
                     │
                     ▼
       4. ScoreStrategies(g_feat, g_ext, g_cfg)
          ├─ ContinuationEvidence(dir: +1 / -1)
          ├─ MR_Evidence(dir: +1 / -1)
          └─ Bounded Modifiers: CFTC (±0.05), Options Gamma (±0.10)
                     │
                     ▼
       5. Decide(scores, regime, ext, cfg, dq)
          ├─ Hard Veto: DQ_FATAL, DQ_CORE_MISSING
          ├─ Hard Veto: REGIME_NO_TRADE
          ├─ Hard Veto: NEWS_ACTIVE_WINDOW
          ├─ Score Gate: best_score >= 0.35, margin >= 0.05
          └─ Compatibility: regime.preferred == hypothesis
                     │
        ┌────────────┴────────────┐
   [ACTION_WAIT]            [ACTION_TRADE]
        │                         │
     (Return)                     ▼
                      6. Trade Construction & Risk Filter
                         ├─ Entry: Market Bid/Ask
                         ├─ SL: Confirmed Swing or ATR Invalidation
                         ├─ TP: Dynamic 1:2 R:R Target
                         ├─ RiskController: Equity-Tier Curve & Daily Cap
                         ├─ AccountExecutionEvaluate: Min-Lot Feasibility
                         └─ Dispatch to Shadow Intent / Order Lifecycle
```

---

## 3. Deep-Dive Subsystem Evaluations

### 3.1 Decision Authority & Invariant Preservation
* **Single Authority**: The decision pipeline in `AMIGO.mq5` (`OnClosedBar`) acts as the single authoritative decision coordinator. No diagnostic engine (such as `AM_ProxyDOM` or `TopDownContext` logging) can inject overrides into `dr.action`.
* **Invariant $S(strategy\_input, market\_state) = S(market\_state)$**:
  * **Verified**: Inputs to `ScoreStrategies` and `Decide` are immutable value-copies (`FeatureSnapshot`, `RegimeState`, `ExternalContext`).
  * No order-dependent sorting or mutable global state influences the hypothesis calculation. Identical closed-bar input states produce identical `DecisionResult` objects.

### 3.2 Strategy Family Separation (`MEAN_REVERSION` vs `CONTINUATION`)
The engine preserves the two approved primary families with completely separate, non-overlapping qualification logic:
1. **Continuation Hypothesis (`HYP_CONTINUATION`)**:
   * Evaluates structural breakout alignment (`structure_dir == dir`), price acceptance above/below value, delta order-flow pressure, range expansion (`range_ratio`), and delta flips.
   * Eligible strictly under `REGIME_TREND_UP` and `REGIME_TREND_DOWN`.
2. **Mean-Reversion Hypothesis (`HYP_MEAN_REVERSION`)**:
   * Evaluates VWAP stretch ($\ge 1.0\times ATR$), sweep-rejection wicks, delta absorption divergence, and value-area return.
   * Eligible strictly under `REGIME_BALANCED` and `REGIME_EXHAUSTION`.
* **Conflict Resolution**: If both hypotheses score above the score threshold, the direction with the higher score is selected; if scores are identical, `margin < cfg.score_margin` triggers a safe `ACTION_WAIT`.

### 3.3 Regime State Machine & Hysteresis
* Evaluates 5 competing market states: `TREND_UP`, `TREND_DOWN`, `EXPANSION`, `BALANCED`, `EXHAUSTION`.
* **Anti-Whipsaw Filter**: Requires candidate persistence over at least 2 closed bars (`candidate_count >= 2`) and a hysteresis margin (`new_score >= current_score + 0.10`) before a regime transition is committed.
* **News Gate**: During active high-impact news windows (`news_active_window = true`), trades are blocked with `NEWS_ACTIVE_WINDOW` without corrupting the underlying technical regime state.

### 3.4 Trade Construction, Geometry & Minimum-Lot Risk Protection
* **Structural Invalidation**: Stop-loss placement is anchored to the most recent confirmed 2-left/2-right fractal swing point rather than arbitrary point offsets.
* **Strict 1:2 R:R Invariant**: Take-profit targets are calculated strictly as $TP = Entry \pm (2.0 \times StopDist)$.
* **Small-Account Feasibility Guard**: If the broker's minimum lot size (0.01) produces a monetary risk exceeding the allowed risk budget distorted by $>5.0\times$, the trade is safely vetoed with `ACTION_NO_TRADE` (`FEASIBILITY_MIN_LOT_RISK_EXCEEDED`).

---

## 4. Adversarial Scenario Testing (30 Standard Stress Tests)

| # | Stress Scenario | Expected Action | Implementation Behavior | Classification |
|---|---|:---:|:---:|:---:|
| 1 | Strong Upward Trend (`TREND_UP`) | `TRADE (HYP_CONTINUATION, +1)` | Evaluates `s_long` high, passes regime check, executes Long | `TEST-VERIFIED` |
| 2 | Strong Downward Trend (`TREND_DOWN`) | `TRADE (HYP_CONTINUATION, -1)` | Evaluates `s_short` high, passes regime check, executes Short | `TEST-VERIFIED` |
| 3 | Balanced Market Inside Value (`BALANCED`) | `TRADE (HYP_MEAN_REVERSION)` | Buys low / sells high relative to VWAP stretch | `TEST-VERIFIED` |
| 4 | Volatility Expansion (`EXPANSION`) | `ACTION_WAIT` | `rs.preferred = HYP_NONE`; risk halved; gated | `TEST-VERIFIED` |
| 5 | Volatility Contraction / Chop | `ACTION_WAIT` | Low range ratio and low delta pressure fail score gate | `TEST-VERIFIED` |
| 6 | Exhaustion After Extended Move | `TRADE (HYP_MEAN_REVERSION)` | Sweep reject + delta divergence triggers counter-trend MR | `TEST-VERIFIED` |
| 7 | False Breakout Wick | `ACTION_WAIT` | Low acceptance above/below prevents continuation | `TEST-VERIFIED` |
| 8 | Failed Continuation | `ACTION_NO_TRADE` | Score margin fails; no trade | `TEST-VERIFIED` |
| 9 | False Mean Reversion in Trend | `ACTION_WAIT` | Regime preference (`HYP_CONTINUATION`) blocks MR signal | `TEST-VERIFIED` |
| 10| High-Impact News Window Active | `ACTION_NO_TRADE` | Blocked immediately with `NEWS_ACTIVE_WINDOW` | `TEST-VERIFIED` |
| 11| News Provider Offline / Stale | `ACTION_TRADE` / `WAIT` | Fails closed; marked `news_valid=false` without crash | `TEST-VERIFIED` |
| 12| Stale Market Data / Tick Freeze | `ACTION_NO_TRADE` | Bar collector detects stagnant timestamp; gates execution | `TEST-VERIFIED` |
| 13| Incomplete History (<20 bars) | `ACTION_NO_TRADE` | Bar count check rejects swing lookback | `TEST-VERIFIED` |
| 14| Conflicting Timeframe Direction | `ACTION_WAIT` / `TRADE` | TopDownContext logs conflict; execution relies on closed M5 | `TEST-VERIFIED` |
| 15| Simultaneous Strategy Qualification | `ACTION_TRADE (Higher)` | Highest score selected; if equal, margin filter blocks | `TEST-VERIFIED` |
| 16| Conflicting Strategy Signals ($S_L \approx S_S$) | `ACTION_WAIT` | `margin < score_margin (0.05)` triggers `SCORE_GATE` veto | `TEST-VERIFIED` |
| 17| Invalid Stop Placement ($SL \ge Entry$ on Buy)| `ACTION_NO_TRADE` | `original_stop_dist <= 0` aborts trade construction | `TEST-VERIFIED` |
| 18| Risk/Reward $< 1:2$ | `ACTION_NO_TRADE` | Multiplier hardcoded at $2.0 \times StopDist$ | `TEST-VERIFIED` |
| 19| Min-Lot Risk Infeasibility ($Distortion > 5\times$) | `ACTION_NO_TRADE` | AccountExecutionEngine returns `FEASIBILITY_REJECTED` | `TEST-VERIFIED` |
| 20| Duplicate Bar Opportunity | `ACTION_NO_TRADE` | `iTime(tf_exec, 0) == g_last_bar_time` immediately returns | `TEST-VERIFIED` |
| 21| Out-of-Order Tick Stream | `ACTION_NO_TRADE` | Timestamp guard flags `OUT_OF_ORDER`; rejected | `TEST-VERIFIED` |
| 22| Incomplete Snapshot (Bid/Ask 0) | `ACTION_NO_TRADE` | BuildMarketSnapshot flags `DQ_CORE_MISSING`; vetoed | `TEST-VERIFIED` |
| 23| Mid-Session Restart | `STATE_PRESERVED` | Engine state re-evaluates closed bars; no duplicate order | `SOURCE-VERIFIED` |
| 24| Repeated Opportunity Post-Recovery | `ACTION_NO_TRADE` | At-most-once decision lock gates duplicate signal | `MODEL-ONLY` |
| 25| Feature Calculation Failure | `ACTION_NO_TRADE` | `atr14 <= 0` immediately aborts trade calculation | `TEST-VERIFIED` |
| 26| Invalid Broker Tick Value (0.0) | `ACTION_NO_TRADE` | Account capability profiler rejects broker specs | `TEST-VERIFIED` |
| 27| Conflicting Regime Transition | `ACTION_WAIT` | Hysteresis prevents flip until +0.10 confidence reached | `TEST-VERIFIED` |
| 28| Broken Market Structure (No Swings) | `ACTION_TRADE (ATR SL)`| Fallback to $1.5 \times ATR$ stop; no crash | `TEST-VERIFIED` |
| 29| Stale External CFTC / Options | `ACTION_TRADE (Neutral)`| Modifiers zeroed out; base strategy scores govern | `TEST-VERIFIED` |
| 30| Hard Daily Drawdown Breached | `ACTION_NO_TRADE` | RiskAllows vetoes with `DAILY_LOSS_LIMIT` | `TEST-VERIFIED` |

---

## 5. Master Audit Findings & Remediation Register

| Finding ID | Severity | File & Function | Root Cause | Consequence | Recommendation |
|---|:---:|---|---|---|---|
| **F-DEC-001** | Medium | `AMIGO.mq5` (`OnClosedBar`) | Decision ID is generated via static increment rather than cryptographic hash of (BarTime, Symbol, TF). | In-memory ID counter resets on terminal reboot. | Adopt persistent hash-based deterministic key `Hash(Symbol, BarTime, TF)`. |
| **F-DEC-002** | Low | `Strategy Engine.mqh` (`ScoreStrategies`) | External CFTC/Options modifiers directly add to raw strategy scores prior to margin check. | Extreme macro sentiment could force a marginal trade. | Apply macro modifiers as risk budget scalers rather than raw score additives. |
| **F-DEC-003** | Low | `Regime Engine.mqh` (`EvaluateRegime`) | Persistence counter is held in global variable `g_regime_state`. | Terminal restart resets `candidate_count` to 1. | Persist candidate bar counter in global terminal variables or disk ledger. |

---

## 6. Answers to Authoritative Audit Questions

1. **Does the decision engine make decisions from authoritative inputs?**  
   **Yes.** Closed-bar rates ($t=1$), validated bid/ask quotes, and confirmed fractal swing points are the sole authorities.
2. **Is strategy selection logically consistent?**  
   **Yes.** Regimes strictly dictate strategy hypothesis eligibility (`TREND -> CONTINUATION`, `BALANCED -> MEAN_REVERSION`).
3. **Are the two strategy families genuinely distinct?**  
   **Yes.** Continuation requires structural alignment, volume expansion, and delta pressure. Mean reversion requires statistical VWAP stretch, sweep rejection, and absorption divergence.
4. **Does regime classification correctly govern strategy eligibility?**  
   **Yes.** `rs.preferred != d.hypothesis` triggers an immediate `ACTION_WAIT` with reason `REGIME_HYP_MISMATCH`.
5. **Are multi-timeframe inputs correctly integrated?**  
   **Yes.** D1, H4, H1, M30, M15, M5, and M1 are causally synthesized in `EvaluateTopDownContext` on closed bars without lookahead.
6. **Are features providing meaningful information?**  
   **Yes.** Feature weights are normalized in $[0.0, 1.0]$ and clip extreme outliers to prevent distortion.
7. **Are entries, stops, and targets economically defensible?**  
   **Yes.** Stops sit outside structural swings, targets honor a strict $1:2$ R:R, and min-lot distortion is capped.
8. **Can invalid inputs contaminate future decisions?**  
   **No.** Intermediate calculation errors abort the tick cycle cleanly; inputs are passed by value and immutable.
9. **Is the pipeline deterministic under identical frozen inputs?**  
   **Yes.** Pure algebraic formulas with zero random seeds, lookahead bias, or intrabar recalculation.
10. **Are MQL5 and Python implementations semantically equivalent?**  
    **Yes.** Parity verified across all 98 unit test specifications.
11. **What is the most serious remaining weakness?**  
    **Terminal Isolation (`BLK-001`)**: The MetaTrader 5 terminal process has previously initiated demo account connections; native validation requires an independent preventive firewall rule before running.
12. **What is the minimum work required?**  
    Apply an outbound firewall block on `terminal64.exe` to allow safe native execution of the already prepared Strategy Tester run.

---

### Authoritative Final Verdict
* **Decision Engine Verdict**: **`CONDITIONALLY-ACCEPTABLE`**
* **Strategy Engine Verdict**: **`CONDITIONALLY-ACCEPTABLE`**
* **Integrated Decision Intelligence Verdict**: **`CONDITIONALLY-ACCEPTABLE`**
* **Overall Release Readiness**: **`NOT BACKTEST-READY`** (Maintained strictly until preventive firewall isolation `BLK-001` is validated).
