# AMIGO quantitative and backtest audit

Audit date: 19 November 2026, Africa/Nairobi. Overall verdict: **NOT READY**.

## 1. Executive assessment

The downloaded quote history is useful research evidence, but downloading ten years of files does not establish a valid ten-year AMIGO backtest. Native AMIGO has substantive scalping, intraday and swing selection/management code. The separate Python backtester does not reproduce that architecture. Its horizon constants do not create horizon-specific strategies or trade lifecycles. Position trading is not implemented in the inspected native selector.

Acquisition completed: **124 ZIP archives, 3,301,979,150 compressed bytes and 504,932,597 original CSV records**, including three pre-roll months and records outside the requested test window. Thirteen archives failed chronological validation: 72,512 backward transitions in total, plus 234,028 adjacent exact duplicate rows. The verified maximum November timestamp is 13 November 2026 16:59:59 in the provider clock, short of the requested end. No ten-year profitability, drawdown, Sharpe ratio or account-growth claim is certified. The requested account-size grid is USD **5, 10, 25, 50, 100, 250, 500, 1,000, 5,000 and 10,000**, with hedging requested. Eighty offline risk-feasibility scenarios were executed across this grid, two hypothetical contract scales and four stop distances. These are analytical probes, not historical account backtests. The Python replay has no hedging/margin model.

The new assignment is audit-only. No strategy source, existing configuration, existing dataset, database, binary or test was edited; no terminal was launched and no Git push occurred during this audit. New source archives were downloaded under the user's explicit instruction. New analysis scripts and reports reside in the Codex workspace. Prior-turn code corrections and remote delivery are separate history, not actions performed under this audit.

## 2. Repository, environment and evidence

Root: `E:\AMIGO-EA31337-REBUILD`; branch `master`; HEAD `48cd514ba1469f86dfc17ffd8613162a254078f8`. The working tree is not clean. Two architecture files have staged and unstaged edits, and the native baseline, Python modules, reports and research data include untracked files. The tested implementation is therefore the **working-tree snapshot**, not HEAD alone. All 55 files in the pre-audit corrected-source manifest still match their SHA-256 values. See `audit_repository_state.json` for exact status.

Instructions reviewed: the supplied comprehensive audit assignment and `README_DEVELOPMENT_GUIDE.md`. Git metadata was read only. Tests used `python -B`, disabled automatic pytest plugins and disabled pytest's cache provider. They write only new XML evidence in the output directory. Inspected selected tests and imported analytical modules contain source reads, in-memory calculations and assertions, not broker connections or project database writes.

Evidence paths below are relative to the stated E: root; line numbers refer to this working-tree snapshot. `SOURCE_EVIDENCE.txt` provides numbered excerpts. VERIFICATION levels distinguish executed Python behavior from inspected MQL5 source. Compilation reported in the earlier correction report is not native runtime evidence.

## 3. Architecture map

Native path: `AMIGO_BASELINE/MQL5/Experts/AMIGO.mq5` → closed M1 opportunity → full closed-interval quote TIB → feature snapshot and seven-timeframe structure → regime state → continuation/mean-reversion scoring → deterministic horizon selection → geometry/risk/account checks → execution journal and position management/recovery. Includes are explicit at EA lines 10–41.

Python baseline: `AMIGO_BASELINE/Python/algomind/` contains risk, account execution, position management and order-flow reference components. Their unit tests do not integrate those components into the separate replay.

Python replay: `Python/backtest_engine.py` directly instantiates MA/RSI and RSI-reversal prototypes, `RiskManager` and `TIBGenerator` (lines 222–244). It never calls the native regime/horizon pipeline or baseline position manager. `ARCHITECTURE/` is another prototype framework; its presence is not evidence of native live/replay parity.

## 4. Horizon implementation matrix

| Requirement | Scalping | Intraday | Swing | Position |
|---|---|---|---|---|
| Independent configuration | Shared config with horizon branches; PARTIALLY VERIFIED | Same | Same | NOT IMPLEMENTED in selector |
| Entry timeframe | M1 source-verified | M1 source-verified | M1 source-verified | Absent |
| Context/authority | Continuation M5+M1, no opposing higher frame | Continuation H1/M30/M15 plus M5/M1 | Continuation D1/H4/H1 plus M5/M1 | Absent |
| Mean-reversion eligibility | Balanced regime, M15/M5 neutral | Balanced regime, H1/M30/M15 neutral | Not selected by native MR branch | Absent |
| Signal generation | Shared hypothesis scorer, then horizon selection | Same | Same | Absent |
| Stop geometry | M1 confirmed structure | M15 confirmed structure | H4 confirmed structure | Absent |
| Risk | Shared equity curve/account constraints | Same | Same | Absent |
| Management | BE at 33% target progress; 1.5R partial; conditional 1h expiry | BE at 50%; configured partial; saved session close | BE at 60%; configured partial; multi-session | Absent |
| Backtest isolation | NOT IMPLEMENTED in Python replay | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED |
| Per-horizon performance | NOT IMPLEMENTED in Python replay | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED |
| Runtime readiness | NOT READY | NOT READY | NOT READY | NOT IMPLEMENTED; NOT READY for claimed support |

Evidence: `Strategy Engine.mqh:37` (`SelectApprovedHorizon`); EA `OnInit:196`, `OnClosedBar:841`; `Position Manager.mqh:345`, `:736`, `:774`, `:987`. Native lifecycle identity is saved and restored in `PositionRecovery.mqh`; the source-integration tests passed. There is one winning decision followed by a longest-context-first selection, not four independent simultaneously arbitrated strategy books. Higher frames can veto the selected direction. The position owns its selected horizon; later configuration does not simply relabel it.

Holding-period caveat: the scalp's 3,600-second exit is conditional on break-even **not** having activated. It is not an unconditional one-hour maximum. Swing has no inspected fixed maximum duration. Entry sessions use configured broker-server hours. This is not yet mapped to HistData's documented fixed EST clock.

The target derives from configured RR times original stop distance (EA:887–892). The ATR used there is the execution feature ATR, while structural invalidation changes by horizon. That distinction must not be described as an H4 ATR stop simply because the swing geometry uses H4 structure.

## 5. Multi-timeframe chronology

PARTIALLY VERIFIED: `Structure Engine.mqh:190` reads shift-1 bars, validates closed sequence and checks the current/closed-bar identities around the read. It independently computes each timeframe's true-range mean from its own closed snapshot. `FeatureVector.mqh:38` similarly validates M1 history. `Chronology Validation.mqh:10` rejects reversed timestamps, invalid prices and inconsistent counts. Existing chronology and top-down tests passed.

Native TIB uses `[closed_bar_time, decision_boundary)` in milliseconds via `CopyTicksRange` (EA:600–620), resets across missed intervals and requires a recently completed TIB. The Python prototype instead updates strategies on every completed TIB without constructing the native M1/context decision pipeline. These are different clocks, even where the imbalance arithmetic agrees.

No complete identical-input historical MQL5/Python replay was executed. Full absence of look-ahead is NOT VERIFIED. Calls with `require_contiguous=false` validate ordering but do not certify that every expected trading bar exists. Broker UTC/DST mapping and file anomalies remain unresolved; adding five hours to every timestamp cannot repair an internally backward sequence.

## 6. Strategy and regime verification

Native continuation combines structure, displacement, acceptance, directional quote-pressure and range support, with flip/surge bonuses (`Strategy Engine.mqh:140`). Mean reversion combines ATR-normalized VWAP stretch, directional rejection, divergence proxy and value return (`:119`). These are different from the Python MA/RSI and RSI-reversal rules.

`Regime Engine.mqh:32–106` scores trend up/down, expansion, balance and exhaustion. Trend gives 45% to higher-timeframe authority; exhaustion requires a sweep rejection and at least 2 ATR extension. `EvaluateRegimeWithState:112` uses persistence/hysteresis and refreshes incumbent confidence from current evidence (:158). Empirical calibration and switching performance are NOT VERIFIED.

NEWS has a case in the regime switch, but is not one of the five scored candidates at :135–141. News admission is separately governed. EA:230 explicitly rejects news-enabled Strategy Tester runs because historical news replay and broker-to-UTC mapping are missing. `Decide:216` applies fatal/core-data and NO_TRADE vetoes, score/margin thresholds and hypothesis compatibility.

Native exhaustion prefers mean reversion, but `SelectApprovedHorizon` admits MR only in BALANCED. Thus an exhaustion/MR decision cannot obtain a horizon via the inspected selector. This is a confirmed reachability conflict, not proof that a separate exhaustion strategy is operational.

## 7. Quantitative signals

| Component | Actual definition/use | Verification/limitation |
|---|---|---|
| Native ATR | Arithmetic mean of true ranges, older closed close in gap terms | Source and independent oracle tests; not Wilder smoothing; native runtime NOT VERIFIED |
| Native volatility | Current closed range / upper-middle prior-20 range; rank versus prior ranges | `FeatureVector:62–83`; volatility rank is not traded-volume rank |
| Structure | Confirmed swing neighborhoods/BOS/sweeps | Bounded closed-array checks tested; historical behavior NOT VERIFIED |
| VWAP/value | HLC3 weighted by broker tick count; typical-price bins and 70% value area | `Auction:88`; PROXY, not exchange volume-at-price |
| Tick imbalance | Sum of bid-change signs; flat quote contributes zero; threshold 100 | Python fixture passed; feed sampling changes bar timing |
| MA/RSI prototype | Mean of last 20 TIB closes, fast half-window; gain/loss arithmetic | Not native strategy parity; trend `rsi_period` is stored but does not govern its computation |
| RSI reversal prototype | Price-step direction plus RSI filters | Not actual independently confirmed divergence; thresholds are assumptions |
| ADX | No ADX dependency identified in inspected active decision path | NOT VERIFIED elsewhere; no ADX performance claim |
| ML | Hook returns unavailable and pass=true when unimplemented | `ML gate hook:29–48`; NOT IMPLEMENTED, enabled behavior conflicts with its fail-closed comment |

Weights, threshold 100, 20/14 windows, regime cutoffs and stop/target constants lack demonstrated out-of-sample calibration in this audit. Names such as pressure, absorption, delta or confidence do not confer statistical or exchange-data meaning. The obsolete `Feature  Vector Assembly.mqh` is not the EA's included `FeatureVector.mqh`; its placeholder values were not attributed to the active path.

## 8. Market data and backtest engine integrity

HistData monthly ZIP archives are stored at `E:\AMIGO-EA31337-REBUILD\research-data\histdata`. See `histdata_acquisition_manifest.json` and `DOWNLOAD_SUMMARY.md` for final counts, hashes, endpoints and rejection reasons. The downloader preserves original ZIP bytes and streams CSV validation without rewriting rows. Hashes establish reproducibility of received bytes, not independent certification of all historical prices.

Provider documentation states Generic ASCII tick columns are DateTime/Bid/Ask/Volume and fixed EST without DST. Volume is not exchange traded volume. No original contributing venue or independently reconciled gold-feed lineage was established. [HistData FAQ](https://www.histdata.com/f-a-q/).

Several October archives contain backward clock jumps near 20:00→19:00 on the final Sunday of October; exact original rows are in `histdata_timestamp_anomalies.json`. A seasonal-clock explanation for those older October examples is plausible but unverified. June–November 2026 also contain thousands of backward transitions, so a seasonal-clock explanation does not resolve the dataset. The anomaly artifact preserves up to 20 exact offending row pairs per affected month. Do not silently sort, drop or relabel them. The existing Python replay rejects backward timestamps (`backtest_engine.py:262`), so these are concrete full-run blockers. Missing periods must not be replaced with generated quotes.

Month existence, valid quotes and successful ZIP CRC do not prove uninterrupted market coverage. The supplied file-status report lists gaps but is not an independently validated market calendar. Daily closures, holidays, same-time ticks and missing active-session observations need separate treatment. Endpoint and warm-up coverage are distinct: the native D1 context requires at least 50 closed bars. Additional August–October 2016 archives were acquired and validated for pre-roll (`histdata_warmup_manifest.json`); constructing broker-aligned D1 bars and demonstrating actual native readiness remain outstanding.

## 9. Execution realism

Python replay has bid/ask entry/exit sides, a later-timestamp entry, stop gap losses, constant user-specified slippage, round-trip commission and calendar-day swap charges. Its geometry is price×0.002 rather than measured ATR/structure (`_execute_trade:344`). It has one position, no pending-order book, rejection/fill latency distribution, partial fills, hedging margin, currency conversion, dynamic historical specifications or broker stop/freeze grids. Native management/recovery is not invoked.

`Account Execution Engine.mqh` dynamically reads account/symbol properties and uses adverse `OrderCalcProfit`, loss-side tick value and `OrderCalcMargin` (:154, :278, :348, :698, :775). This is stronger source-level machinery than the prototype, but historical specifications, commissions, swaps and tester runtime remain NOT VERIFIED. Account labels such as cent/standard do not establish contract size; USD equity cannot be confused with cent-denominated balance units.

No installed terminal was used. The existing `Python/safe_backtest.ini` selects M5 execution and news mode 1, both incompatible with current EA initialization guards. It is also shadow-only and covers only Q1 2026. Running it would not satisfy the requested decade or produce executable hedge-account evidence. It was not changed or launched.

## 10. Risk and account-size scenarios

Selected regression tests verify actual Python missing-metadata rejection, tick-unit sizing, volume flooring, unsafe minimum-lot rejection, absolute cap, daily gate and no drawdown throttle. Native source enforces 2% daily configuration and maximum distortion 5.0 (EA:194), and blocks non-tester live execution (:191).

The baseline reference curve starts at 1.5% for very small accounts and reaches 0.5% at $500; allowed distortion varies with equity. The separate prototype uses fixed 0.5% and maximum 5.0 (`RiskManager:162`). That is a material small-account CONFLICT, not equivalent sizing.

`account_scenario_audit.json` contains 80 executed scenarios. Assumed standard contract: tick size .01, $1/tick/lot, minimum .01 lot, round-trip commission $7/lot and slippage .10 price units. A second hypothetical contract is one-hundredth the cash scale; it is **not** certified as any broker's cent account. At $5, every tested standard-contract stop distance (1, 5, 20, 50 price units) is infeasible under the 2% ceiling. The smaller-contract 1 and 5 unit cases pass this limited cash-risk probe; margin, spreads, execution and historical trade profitability were not established. No minimum-lot trade was forced.

## 11. MVE mathematics

Native `RiskControllerGetMinimumViableEquity:173` and Python `calculate_minimum_viable_equity:134` bracket/bisect the first crossing of E×R(E)/100×D for supplied fixed D. The compatibility risk-percent argument does not freeze R(E). The normal-equity helper sets D=1. This matches the requested mathematical definition for the approved curve, whose E×R(E) is nondecreasing across its segments.

Executed Python fixture: minimum-lot loss $10 and D=5 → MVE approximately $276.393202250021; normal threshold $2,000. The slightly lower equity fails the crossing. Native runtime equality remains NOT VERIFIED. MVE is diagnostic, not permission to ignore the separate 2% cap, margin, cost, daily-lock or symbol-grid checks. The Python optional custom curve is not passed into this static default-curve solver; arbitrary custom-curve equivalence is NOT VERIFIED.

## 12. Metrics and statistical validity

`_generate_report:376` calculates count, win rate, gross positive/negative closed-trade P/L, balance net profit, profit factor, arithmetic net expectancy and tick-marked percentage drawdown. It returns open position separately rather than adding its marked value to final balance/net profit. No native per-horizon performance calculation was demonstrated.

The analytical swap probe reproduces a ledger mismatch: closed trades +100/−50, separate swap −10 → net profit 40 but gross profit minus gross loss 50. Consequently reported profit factor and average trade wins/losses omit separately booked swap, while balance net includes it. The identity requires a separately reported swap adjustment; that adjustment is absent. Break-even trades count as losing trades. No-loss profit factor is infinity, and the no-closed-trades branch returns an error even if an open trade exists. These require explicit metric semantics.

The equity list stores every tick and `_generate_report` creates additional NumPy arrays. A full decade and multiple balances cannot be presumed memory-safe. Sharpe, Sortino, Calmar, recovery factor, holding/exposure statistics, confidence intervals and tail risk are NOT IMPLEMENTED in this report generator. No credible statistical sample of actual native trades was produced, so no economic confidence is asserted.

## 13. Robustness and out-of-sample testing

No executed walk-forward, held-out period, bootstrap, parameter sensitivity, trade-order Monte Carlo or broker-execution stress result establishes robustness of this implementation. Numerical regression scenarios are not profitability robustness tests. Retrospective thresholds and feed changes can affect TIB frequency, trade counts and regime behavior. Current data retrieval must not be described as ten-year out-of-sample validation. ML is unimplemented in the inspected active hook, so no trained-model leakage conclusion is available.

## 14. Instrument and broker generalisation

Native symbol metadata is dynamic; the Python replay accepts an explicit specification dictionary but uses a fixed linear cash-per-price conversion, fixed costs and a percentage-of-price stop. EURUSD, GBPUSD, USDJPY and BTCUSD have not been backtested in this audit. XAUUSD HistData quotes are not evidence of XAUUSDm broker spreads or execution. Broker suffixes are labels, not a conversion rule. Hedging, leverage, margin and contract history remain required inputs for valid account-size comparisons.

## 15. Microstructure classification

TRUE within received records: timestamp, bid, ask and derived quoted spread. PROXY: signed bid changes, quote imbalance, tick count, velocity, footprint pressure, HLC3 tick-weighted VWAP, activity profile and proxy DOM. LIMITED: source lineage, missing-tick observability and historical executable liquidity. MISSING: actual aggressive trade signs, exchange volume/delta, queue priority, order-book depth, hidden liquidity and fill/rejection histories. None of the proxy labels should be marketed as exchange order flow.

## 16. Python/MQL5 parity

PARTIALLY VERIFIED for selected pure arithmetic through tests; NOT VERIFIED for identical-input native execution. Source checks confirm native horizon identity through decision, intent, registration and recovery. `orderflow_lab/tests/test_python_mql5_parity.py:28` defines a **Python** `MQL5ParitySimulator`; passing it is Python-versus-Python/reference evidence, not execution of MQL5. Known behavioral differences include strategy families, decision timing, risk curve, regime gating, stop geometry, hedging/margin and all horizon-specific exits.

## 17. Tests actually executed

| Batch | Collected/passed | Failed/skipped | Evidence |
|---|---:|---:|---|
| Quant regression + selector, saved horizon, identity, ladder, proxy math, top-down volatility | 56 / 56 | 0 / 0 | `audit_tests.xml` |
| Existing horizon and Python-reference parity tests | 16 / 16 | 0 / 0 | `horizon_tests.xml` |
| Completion ordering, chronology bounds, risk arithmetic | 30 / 30 | 0 / 0 | `guard_tests.xml` |
| New offline analytical probes | 80 risk scenarios and one metric example | Not pytest assertions | `account_scenario_audit.json` |

Total existing tests: **102 passed**, no failures/skips. Exact commands and per-file counts are in `TEST_EXECUTION.md`. All were inspected for side effects. No native runtime test, broker transaction, historical hedge-account backtest or full-system parity test passed in this audit.

## 18. Findings register

| ID / severity / classification | Evidence and consequence |
|---|---|
| F01 P0 ENGINEERING GAP | `Python/backtest_engine.py:222`, `:295`, `:338`: replay lacks native horizons/regimes/lifecycle. Its returns cannot represent combined AMIGO or separate horizons. Confirmed source divergence; source/reference tests do not cure it. |
| F02 P0 CONFLICT | HistData original backward rows (older Octobers and June–November 2026) in `histdata_timestamp_anomalies.json`; replay rejects backward timestamps at `backtest_engine.py:262`. Full causal replay fails unless provenance-backed chronology treatment is established. No repair applied. |
| F03 P1 CONFLICT | `RiskManager.__init__:162` fixed .5% versus `algomind/risk_controller.py:58–106` equity curves. Eighty probes executed. Especially material to $5–$500 sizing and account comparability. |
| F04 P1 ENGINEERING GAP | `BacktestEngine.__init__:241`, `_execute_trade:341`: only one position; no margin/account-mode engine. Requested hedging account simulation absent. |
| F05 P1 CONFLICT | `Python/safe_backtest.ini` M5/news=1 versus EA `OnInit:196`, `:230`; existing preset would fail current guards and is not a decade test. Source verified, not launched. |
| F06 P1 ENGINEERING GAP | `run_backtest:267–270`, `_generate_report:376`: swap charged outside trade P/L, open P/L excluded from final balance return. Analytical probe confirms inconsistent all-cost metrics; true economic PF not established. |
| F07 P1 PARTIALLY VERIFIED | `TransactionRecon.mqh:166–219`, `:657`: confirmed outcomes increment, rejections do not; journal transition prevents normal duplicate completion. Restart reconstructs by **decision** day rather than actual fill day. Midnight/delayed-fill quota correctness is NOT VERIFIED and can misattribute entries. |
| F08 P1 CONFLICT | `Regime Engine:202` prefers MR in exhaustion; `Strategy Engine:59` allows MR horizon only for BALANCED. Exhaustion MR is unreachable through this selector. |
| F09 P2 REQUIRES DECISION | `Position Manager:741`, `:774`: conditional scalp expiry and 1.5R partial. Decide whether requested minimum RR2 applies only initial full-target geometry or every realized partial exit; do not silently change it. |
| F10 P2 ENGINEERING GAP | `ML gate hook:29–48`: enabled unimplemented hook still passes. Disabled default limits current impact, but fail-closed contract is not met if enabled. |
| F11 P2 ENGINEERING GAP | `backtest_engine.py:336`, `:398`: per-tick Python list plus array copies; decade-scale resource safety unverified. No engine rewrite performed. |
| F12 P2 PARTIALLY VERIFIED | `Structure Engine:204` needs at least 50 closed bars. August–October 2016 pre-roll archives now validate, but native D1 construction/readiness has not been executed. |
| F13 P2 NOT VERIFIED | Historical broker costs/specs/session mapping and active-session completeness absent. Provider quotes alone cannot certify fills, margin or exact date-window coverage. |
| F14 P3 CONFLICT | Horizon tests describe M5 and swing MR combinations while native execution is M1 and native MR selector excludes swing. Passing those fixtures does not prove those native paths exist. |

## 19. Missing requirements and decisions

Authoritative historical broker/account specifications (including real cent denomination if used), leverage and hedged-margin policy; commissions/swaps over time; UTC/server/DST mapping; timestamp anomaly interpretation; warm-up start; explicit RR interpretation for partial exits; expected per-horizon concurrency; treatment of open terminal positions in return metrics; validated news-history policy; and acceptance rules for missing ticks are unresolved. Account-size range is resolved: $5–$10,000 on the stated grid.

## 20. Prioritised remediation roadmap — not implemented

First establish a provenance-backed resolution for the backward October timestamps and the missing tail after 13 November 2026, preserving all original ZIPs. Then prepare an isolated native quote-import/replay acceptance fixture with historical symbol/account specifications and adequate warm-up. Prove initialization and horizon lifecycle on a short slice before a ten-year sweep. Repair the separate prototype only if it is explicitly chosen as the performance engine; otherwise do not present it as native parity. Reconcile metric ledgers and quota midnight cases before economic acceptance. Perform held-out/stress analysis only after execution validity.

## 21. Explicit final answers

1. All intended horizons implemented? Native scalp/intraday/swing branches exist; independent runtime support is not certified; position absent.
2. Backtester preserves independence? No: the inspected Python replay does not preserve horizon identity or policies.
3. Free from look-ahead? Closed-bar safeguards partially verified; full historical claim NOT VERIFIED.
4. Strategy/regime causally valid? Source is predominantly closed-snapshot based; pipeline parity and historical behavior NOT VERIFIED; exhaustion/MR conflict confirmed.
5. Realistic costs? Partial constant-cost prototype only; historical broker realism NOT VERIFIED.
6. Risk correct? Selected baseline arithmetic verified in Python, native runtime not verified, prototype curve conflicts.
7. Five executed entries/day? Core source transition observed; midnight/restart and native transaction behavior NOT VERIFIED.
8. Python/MQL5 consistent? No, significant known behavioral differences.
9. Metrics correct? Some elementary formulas are present; swap/open-equity semantics prevent complete cost-adjusted acceptance.
10. Sufficient statistical evidence? No.
11. Principal blockers? Timestamp anomalies, native replay not established, missing horizon/hedging parity, cost/specification gaps, metric inconsistencies and unverified native warm-up readiness.
12. Next narrowly scoped task? Resolve timestamp provenance and document an immutable, causal quote sequence for one affected October before importing it into an isolated native replay.

Overall readiness verdict: **NOT READY**. Downloads and passing analytical/source tests are useful evidence, but are not proof of profitable or operational multi-horizon trading.
