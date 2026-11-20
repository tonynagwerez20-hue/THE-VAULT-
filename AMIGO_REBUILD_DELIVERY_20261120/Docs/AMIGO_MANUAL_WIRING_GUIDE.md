# AMIGO manual wiring guide

This is the practical “assemble it piece by piece” description of the current AMIGO rebuild. It describes the code that exists, not an aspirational architecture. The authoritative execution file is `AMIGO_BASELINE/MQL5/Experts/AMIGO.mq5`.

## 1. What AMIGO is

AMIGO is a layered XAUUSD decision-and-execution system. It is not one indicator and it is not Python placing trades. The intended authority chain is:

```text
MT5 ticks/bars
  -> validated market snapshot
  -> feature snapshot
  -> top-down context + regime
  -> continuation / mean-reversion scores
  -> selected horizon
  -> TIB and microstructure confirmation
  -> news/external-context checks
  -> risk ledger and account feasibility
  -> trade intent validation
  -> broker execution
  -> transaction reconciliation
  -> position lifecycle management
```

Every arrow is a gate. A failure normally means “no trade,” not “try anyway.” That is why a correctly attached EA can produce zero trades.

MQL5 owns the final decision, risk, order submission, position management, and reconciliation. Python is for research, historical data, external context, and offline experiments; it must not bypass MQL5 risk gates.

## 2. The physical pieces

Think of the installation as a cabinet with separate trays.

### Tray A: MT5 executable

- `AMIGO_BASELINE/MQL5/Experts/AMIGO.mq5` is the source.
- `AMIGO_BASELINE/MQL5/Experts/AMIGO.ex5` is the compiled binary.
- The active terminal copy is under the MetaQuotes terminal data directory in `MQL5/Experts`.
- The EA reads broker symbol properties, account equity, tick history, bar history, permissions, and trade responses from MT5.

### Tray B: MQL5 include modules

- `Contracts header.mqh`: enums and shared records such as horizons, hypotheses, features, intents, and external context.
- `Configuration.mqh`: the runtime configuration structure.
- `Bar Collector.mqh`: completed-bar reads and ATR calculation.
- `Market Snapshot Builder.mqh`: freezes the market state at one M1 decision boundary.
- `FeatureVector.mqh`: converts the frozen snapshot into normalized features.
- `Regime Engine.mqh`: classifies the market state using top-down context and features.
- `Strategy Engine.mqh`: scores continuation and mean reversion and selects a decision.
- `TickImbalanceBars.mqh`: creates closed tick-imbalance bars from quote ticks.
- `Risk Engine.mqh` and `RiskController.mqh`: persistent ledger, daily stop, sizing feasibility, and admission.
- `Execution Engine.mqh`: validates and submits the order.
- `Position Manager.mqh`: restores, registers, trails, partially closes, and reconciles positions.
- `TransactionRecon.mqh`: journals requests, orders, deals, and outcomes.
- `External Context Compactor.mqh`: parses the external bridge file and publishes validated snapshots.
- `News Policy.mqh`: applies news freshness and horizon-specific news rules.

### Tray C: Python research

The Python side contains tick download/validation, TIB generation, offline backtesting, account sweeps, experiment registration, and reports. It is useful for hypothesis testing but is not native MT5 parity until the same data semantics, costs, timestamps, and execution outcomes have been demonstrated in MT5.

### Tray D: external bridge

The bridge file is configured by `InpBridgeInbox` and `InpBridgeOutbox`. The inbox is expected to contain a schema-versioned key/value payload containing fields for CFTC positioning, options context, and news. Invalid, stale, duplicated, or incomplete fields are rejected. In tester mode, the live bridge is deliberately disabled, so those fields cannot silently become look-ahead data.

## 3. Startup wiring

When AMIGO is attached, `OnInit()` performs the following sequence:

1. Validates fixed timeframe requirements: D1, H4, H1, M30, M15, M5, and M1.
2. Validates score, partial-exit, trailing, news, and TIB inputs.
3. Selects the configured symbol or the chart symbol.
4. Builds the shared configuration object.
5. Acquires the position-state namespace so two instances cannot manage the same state.
6. Restores the persistent risk ledger. If it is absent or ambiguous, admission remains blocked unless explicit initialization is enabled.
7. Restores adaptive-risk state.
8. Opens the execution journal and checks unresolved prior outcomes.
9. Reconciles persisted position state with broker positions.
10. Starts the five-second management timer.
11. Runs broker audits such as tick size, tick value, contract size, minimum lot, and `OrderCalcProfit`.

The important distinction is “attached” versus “ready.” An attached EA can be visible on a chart while the risk or reconciliation state is quarantined.

## 4. The first wire: OnTick and the fail-closed gates

On every tick, AMIGO now prints a throttled gate diagnostic before returning:

```text
[RUNTIME_GATE][OnTick] owner=OK/BLOCKED admission=OK/BLOCKED risk_ready=OK/BLOCKED
```

Interpretation:

- `owner=BLOCKED`: another instance owns the state namespace or the ownership identity is invalid.
- `admission=BLOCKED`: position state, stop protection, or reconciliation has a fault latch.
- `risk_ready=BLOCKED`: the risk ledger, adaptive risk state, or execution journal has not been safely recovered.

Only after these gates pass does AMIGO update risk, read the tick, refresh external context, and look for a new closed M1 bar.

## 5. The decision clock

AMIGO does not make a new decision on every tick. It uses the opening of a new execution-timeframe bar as the decision boundary and evaluates the fully closed previous bar.

For M1:

```text
bar 10:05:00 opens
bar 10:04:00–10:04:59 is now closed
AMIGO evaluates the 10:04 closed bar at the 10:05 boundary
```

The code checks that the bar times are positive, ordered, stable, and not moving backward. It reserves a durable opportunity identity before analysis to prevent duplicate decisions after restart or repeated ticks.

## 6. TIB wiring

TIB is not a second strategy. It is a confirmation/risk governor.

1. AMIGO requests all quote ticks in the closed M1 interval with `CopyTicksRange`.
2. It rejects invalid quotes, backward timestamps, missing bid/ask, or `ask < bid`.
3. `TickImbalanceBars` accumulates signed quote imbalance until the configured threshold is reached.
4. Only a closed TIB bar is eligible for the decision.
5. The feature vector receives availability, signed imbalance, tick count, direction, and ATR-normalized intensity.
6. The strategy engine vetoes a candidate when TIB direction opposes it.
7. Same-direction TIB intensity can increase evidence, but cannot create a trade from nothing.

The current default is `InpTIBThreshold=100` and `InpTIBEnabled=true`. A threshold that is too large can produce few closed TIB bars; a threshold that is too small can make the feature noisy.

## 7. Top-down wiring and horizons

All entries are physically executed on M1. The horizon describes the context and lifecycle policy, not a separate order engine.

### Scalping

- Required directional context: M1 execution direction and M5 confirmation.
- Uses the shortest holding expectation.
- M1 adverse microstructure is an immediate veto.
- Position management uses the shorter partial target policy.

### Intraday

- Continuation requires compatible H1, M30, and M15 structure.
- Mean reversion requires a balanced regime and neutral H1/M30/M15 context.
- M1 is still the entry clock, but M1 pressure cannot prove a multi-session trend.

### Swing

- Continuation requires D1, H4, and H1 alignment.
- The entry is still generated on a closed M1 boundary.
- The position manager applies the longer lifecycle policy; it does not turn MT5 into a daily-bar execution engine.

The horizon selector rejects contradictory higher-timeframe directions. A score alone cannot force a horizon.

## 8. Strategy wiring

AMIGO has two primary hypotheses.

### Continuation/trend

Evidence includes structure direction, displacement, acceptance, normalized pressure, range expansion, delta flip, surge, and compatible TIB direction. An opposing TIB direction returns zero continuation evidence.

### Mean reversion/value

Evidence includes ATR-normalized VWAP stretch, rejection/sweep behavior, divergence, and value-state return. The direction must be aligned with the stretch: long mean reversion is expected below VWAP; short mean reversion above VWAP. An opposing TIB direction returns zero mean-reversion evidence.

The strategy engine then compares long continuation, short continuation, long mean reversion, and short mean reversion. It requires a score threshold and a minimum margin. If the best side does not clear both, the result is `ACTION_NO_TRADE`.

## 9. Indicators and data realism

The active AMIGO EA does not contain RSI, MACD, or Stochastic. Those indicators are not silently driving the strategy.

ATR is used for:

- volatility normalization;
- structural stop selection;
- spread relative to stop-distance filtering;
- trailing and lifecycle calculations;
- TIB imbalance normalization.

VWAP, footprint, activity profile, and DOM-like fields are broker-tick proxies. MT5 spot gold does not provide centralized CME order flow through the ordinary symbol feed. These features must therefore be labelled as proxies and validated per broker.

## 10. External services

CFTC and options data are slow context, not entry triggers. They are read through the bridge, validated for publication time and schema, and capped by `InpCFTCMaxInfluence` and `InpOptionsMaxInfl`.

News is different: it can be an admission veto. `InpNewsMode=0` is required for the current tester because historical news replay and broker-to-UTC mapping are not implemented. Live news-enabled operation requires a fresh, schema-correct external payload.

The safe external sequence is:

```text
Python/provider writes complete temporary payload
  -> atomically publishes Amigo_ext_in.txt
  -> MT5 reads and validates it
  -> stale/invalid payload becomes unavailable
  -> news policy or external-data quality can veto admission
```

## 11. Risk and execution wiring

The current loss policy is:

- per-trade risk: `InpRiskPerTrade`;
- daily loss stop: `InpDailyLossPct=2.0`;
- daily entry cap: five new entries;
- minimum-lot and broker feasibility checks;
- spread and stop-distance checks;
- margin and account permissions;
- position-capacity and duplicate-intent checks;
- total/account-wide DD lock: disabled as requested.

Risk sizing uses actual equity, stop distance, tick value, tick size, volume minimum, volume step, and broker profit calculations. Small accounts may still be infeasible because the minimum lot can risk more than the intended percentage. `InpAllowMinLotOverride` permits bounded distortion, but it does not guarantee a trade.

After strategy approval, AMIGO creates a `TradeIntent`, validates identity, symbol, direction, timestamps, stops, target, horizon, and risk allocation, then calls the execution engine. A broker-accepted result is not considered complete until the transaction journal and visible managed position agree.

## 12. Position lifecycle

After a confirmed fill:

1. The position must be visible with the expected symbol, magic number, direction, and volume.
2. It is registered with entry, stop, target, ATR, and horizon.
3. Protective stop state is persisted.
4. The timer manages trailing, partial exits, and horizon-specific lifecycle rules.
5. Any ambiguous outcome latches admission and requires reconciliation.

This is intentionally conservative. It can reduce trading frequency, but it prevents an unknown broker state from being treated as safe.

## 13. Why a tester can show zero trades

Check the causes in this order:

1. Tester date begins before the first available real tick.
2. `RUNTIME_GATE` reports `risk_ready=BLOCKED` because of an old journal or risk ledger.
3. TIB has no closed bar in the interval.
4. top-down history is incomplete or mixed at the decision boundary.
5. continuation/mean-reversion score or margin fails.
6. horizon eligibility fails.
7. news mode is nonzero in tester.
8. spread, stop distance, minimum lot, margin, or account permissions fail.
9. execution is accepted but reconciliation cannot confirm the position.

The correct proof of a trade is an actual MT5 transaction/deal record, not a startup diagnostic saying `SIGNAL_VALID_EXECUTABLE`.

## 14. How the EA31337 rebuild relates to AMIGO

EA31337 is the reference/base ecosystem and class library lineage. AMIGO is the rebuilt application layer placed on top of that general MQL5 environment.

The rebuild keeps the platform-facing concerns—MQL5 symbol/account APIs, trade requests, history, timers, and broker constraints—but replaces a monolithic “indicator says buy” approach with explicit AMIGO contracts:

```text
snapshot -> features -> regime -> hypothesis -> horizon -> intent -> risk -> execution -> reconciliation
```

The reverse-wiring order is therefore:

1. Start at the broker-facing `Execution Engine` and `TransactionRecon` contracts.
2. Connect `Risk Engine`, `RiskController`, and `Position Manager` above execution.
3. Connect `TradeIntent` validation so strategy output cannot submit malformed orders.
4. Connect `Strategy Engine` and its two hypotheses.
5. Connect `Regime Engine` and top-down context.
6. Connect `FeatureVector` and completed-bar snapshot construction.
7. Connect TIB to the closed quote-tick interval.
8. Connect external context as bounded, optional input—not as execution authority.
9. Connect Python research and backtesting as a parallel evidence system.

That ordering is important: if you build from indicators upward and leave risk/reconciliation until last, you can make a backtest signal but not a safe EA. AMIGO is intentionally wired from the broker safety boundary inward.

## 15. Current honest status

- Source compiles cleanly.
- The total-DD change is applied.
- Runtime gate diagnostics are deployed.
- TIB, horizons, strategy interaction, and external schemas are structurally connected.
- Native MT5 profitability and trade frequency are not proven by compilation.
- The next meaningful acceptance test is a fresh real-tick tester run with aligned dates and a journal showing actual order/deal transactions.
