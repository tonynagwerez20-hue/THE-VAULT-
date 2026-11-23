# AMIGO — AUTONOMOUS SYSTEM RECOVERY, RESEARCH, ENGINEERING, OPTIMISATION AND VALIDATION

## 1. YOUR ROLE AND MISSION

You are the principal systems architect, quantitative researcher, MQL5 engineer, Python engineer, data engineer, testing engineer and technical auditor responsible for bringing the AMIGO trading system to its intended state.

You have broad autonomous authority to inspect, research, modify, repair, upgrade, test and optimise the AMIGO project.

Your mission is to deliver a functioning, mathematically defensible, integrated and economically viable retail algorithmic trading system.

This is not a request to build a new trading bot from scratch.

You must recover and understand the original AMIGO project, its intended functionality, its architectural decisions, its previous research, its implementation history and the upgrades proposed throughout its development.

Do not discard useful existing work simply because you believe a different implementation would be easier.

Do not preserve defective implementations merely because they already exist.

Your responsibility is to distinguish between:
- Original functionality that must be preserved.
- Functionality that was intended but never implemented.
- Implemented functionality that is defective.
- Improvements that have a defensible theoretical or empirical basis.
- Experimental features that have not demonstrated an edge.
- Unnecessary complexity that should be removed.

The ultimate objective is a practical system that works reliably, not an unnecessarily sophisticated architecture.

**Engineering principle: The simplest implementation that correctly satisfies the intended mathematical, trading and operational requirements is preferred.**

You have authority to make necessary engineering decisions without repeatedly requesting permission.

However, all changes must be traceable, tested and justified.

---

# 2. FIND THE AMIGO PROJECT FIRST

Do not assume the repository is located in the current working directory.

I may have moved the project between my laptop, desktop, external drives or development directories.

Start by identifying the available development environment and searching for the actual AMIGO project.

On Windows, inspect relevant locations, including:

- Desktop.
- Documents.
- Downloads.
- Development directories.
- Projects directories.
- OneDrive directories, where accessible.
- Other local drives, particularly C: and E:.
- Git repositories.
- Folders containing AMIGO.mq5.
- Folders containing AMIGO-related `.mqh`, `.py`, `.json`, `.yaml`, `.toml`, `.csv` and configuration files.

Look for:
- AMIGO.mq5.
- AMIGO include directories.
- Regime Engine.mqh.
- Strategy Engine.mqh.
- FeatureVector.mqh.
- Risk and execution modules.
- Python bridge and external services.
- Data ingestion scripts.
- News and macro infrastructure.
- Configuration files.
- Historical datasets.
- Test harnesses.
- Documentation and architecture decisions.
- Git repositories and previous development branches.

Also search for extracted AMIGO repositories and related THE-VAULT project history where relevant.

Do not modify THE-VAULT or unrelated repositories.

### Repository discovery rules

1. Identify every plausible AMIGO project directory.
2. Establish which one is the active and authoritative repository.
3. Compare duplicate copies using Git history, commit identifiers, file hashes and implementation completeness.
4. Identify uncommitted work and untracked files.
5. Identify the latest known implementation and research decisions.
6. Produce a repository inventory.
7. If multiple plausible authoritative copies exist, compare them before selecting one.

Do not automatically select the most recently modified folder.

If the authoritative repository cannot be established, stop before making modifications and explain the conflict.

Once identified, establish a recoverable baseline and work on a dedicated local engineering branch.

Preserve the original repository and existing work. Do not overwrite or delete historical datasets, configurations or user-created files without a demonstrated necessity.

---

# 3. RECOVER THE ORIGINAL AMIGO VISION

Before implementing anything, reconstruct the intended system from:

- Existing source code.
- Git history.
- Commit messages.
- Previous architecture documents.
- Research notes.
- Test fixtures.
- Configuration files.
- Existing Python services.
- Existing MQL5 modules.
- Historical engineering decisions.

The following is the intended baseline. Treat the actual repository and recorded decisions as the evidence for implementation details.

## 3.1 Core trading philosophy

AMIGO is a retail algorithmic trading system combining:

1. Mean/value reversion.
2. Trend/continuation trading.

These are the core strategy families.

Scalping, intraday and swing trading are trading horizons through which these strategies operate. They must not become three unrelated trading systems.

The system must understand when a strategy is appropriate, when its conditions are absent and when trading should be prohibited.

Do not introduce unrelated strategy families simply to increase signal frequency.

## 3.2 Instruments

Inspect existing support for:

- XAUUSDm / XAUUSD.
- EURUSD.
- GBPUSD.
- USDJPY.
- BTCUSD.

Do not assume that broker symbol specifications are identical.

Validate contract size, tick size, tick value, volume minimum, volume step, volume maximum, digits, stop levels, trading sessions and account-specific constraints.

XAUUSDm is an important reference instrument, but do not hardcode assumptions that break other instruments.

## 3.3 Trading horizons

Implement and verify the integration of:

- Scalping.
- Intraday.
- Swing.

Each horizon must have a defined role, trading conditions, holding-period expectations, risk implications and relevant timeframe evidence.

Avoid creating independent duplicate strategy engines.

The existing strategy logic should be reused wherever possible.

---

# 4. MULTI-TIMEFRAME TOP-DOWN ANALYSIS — D1 TO M1

This is a major requirement.

Investigate whether the existing AMIGO architecture genuinely incorporates higher-timeframe information into lower-timeframe decisions.

The system must support the complete timeframe hierarchy:

D1 → H4 → H1 → M30 → M15 → M5 → M1.

The objective is not to make every timeframe independently generate a trade signal.

The objective is to establish a coherent market-state interpretation across timeframes.

### Required investigation

Determine:

1. Whether D1 establishes the broader market structure and directional environment.
2. Whether H4 identifies the intermediate structure and important value areas.
3. Whether H1 identifies intraday directional conditions and developing structure.
4. Whether M30 and M15 provide intermediate confirmation.
5. Whether M5 identifies actionable trading conditions.
6. Whether M1 provides execution-level information without overriding the broader market context.

These are intended analytical roles, not mandatory indicator assignments. Research and validate the appropriate implementation.

### Required functionality

- Higher-timeframe market structure.
- Directional alignment and conflict detection.
- Trend strength and regime identification.
- Volatility expansion and contraction.
- Value-area positioning.
- Relevant swing highs and lows.
- Liquidity and structural context.
- Entry-timeframe confirmation.
- Conflicting-timeframe handling.
- Missing or incomplete timeframe data handling.

### Critical mathematical requirement

Do not simply average directional signals from all timeframes.

Different timeframes contain different information, sampling characteristics and degrees of dependence.

Research an appropriate hierarchical aggregation method.

Investigate:
- Conditional probability and Bayesian updating.
- Multi-resolution time-series analysis.
- Regime-conditioned signal weighting.
- Correlation and dependence between timeframe features.
- Information redundancy.
- Temporal stability.
- Higher-timeframe information leakage.

The model must avoid double-counting correlated evidence.

### Closed-bar and temporal integrity

Higher-timeframe features must use information that was genuinely available at the decision timestamp.

Do not use unfinished higher-timeframe candles as if their final values were already known.

Where intrabar information is deliberately used, explicitly identify it and ensure that historical testing reproduces the same information availability.

### Acceptance criteria

A trade decision must be explainable in terms of:

- Higher-timeframe context.
- Intermediate timeframe confirmation.
- Entry timeframe conditions.
- Strategy compatibility.
- Conflicts or missing information.
- Risk feasibility.

If the higher-timeframe context is unavailable or materially contradictory, the system must apply a documented policy rather than silently inventing confirmation.

---

# 5. REGIME ENGINE

Audit and improve the existing Regime Engine.

The intended regime classifications are:

- TREND_UP.
- TREND_DOWN.
- BALANCED.
- EXPANSION.
- EXHAUSTION.
- NEWS.
- NO_TRADE.

Investigate whether the current classification mathematics is statistically and economically meaningful.

Check:
- Trend identification.
- Volatility classification.
- Range detection.
- Structural transitions.
- Regime persistence.
- False regime switching.
- Hysteresis.
- Transition delays.
- Conflicting timeframe classifications.
- Regime uncertainty.

Do not introduce arbitrary thresholds without justification.

Where possible, use research-supported statistical methods and calibrated thresholds.

The regime engine must distinguish between a genuine regime transition and temporary noise.

It must also communicate the resulting market state to the strategy engine.

Do not allow a regime classification to become an independent trade signal.

---

# 6. STRATEGY ENGINE

Audit both original strategy families.

## 6.1 Mean/value reversion

Investigate the mathematical foundations of:
- VWAP.
- Value-area high and low.
- Value displacement.
- Mean reversion.
- Volatility-adjusted deviations.
- Market balance.
- Rejection and acceptance.
- Reversion probability.
- Regime dependence.

Determine whether the existing VWAP and value-area calculations are internally consistent and whether the trading assumptions are supported by evidence.

## 6.2 Trend/continuation

Investigate:
- Directional structure.
- Swing progression.
- Trend persistence.
- Pullbacks.
- Momentum.
- Volatility-adjusted continuation.
- Structural invalidation.
- Regime compatibility.

Do not allow the two strategy families to issue contradictory instructions without an explicit conflict-resolution mechanism.

## 6.3 Strategy invariants

Preserve the conceptual relationship:

S(strategy_input, market_state) = S(market_state)

The strategy must respond to market conditions, not silently change its underlying rules because of account size or unrelated execution conditions.

Account-specific risk and broker feasibility must remain separate from strategy intelligence.

You may revise mathematical models where research supports improvement, but document exactly what changed and why.

---

# 7. ORDER-FLOW AND MARKET MICROSTRUCTURE

Investigate the existing order-flow architecture and all related features.

The objective is to improve the quality of market information available to AMIGO without falsely claiming access to institutional central order-book data.

Distinguish clearly between:

1. Genuine exchange order-book information.
2. Genuine exchange-traded volume.
3. Broker-provided tick volume.
4. Tick-direction and price-movement proxies.
5. Derived footprint-style representations.

MT5 retail tick data must not be presented as genuine CME/COMEX bid/ask depth or centralized order flow.

### Investigate

- Tick ingestion.
- Bid/ask changes.
- Tick-direction classification.
- Rolling volume bins.
- Delta approximations.
- Volume imbalance proxies.
- Footprint-style aggregation.
- Session-based profiles.
- Liquidity sweeps.
- Absorption proxies.
- VWAP.
- VAH/VAL.
- M1–H4 aggregation.
- Data-quality classification.
- Memory and computational efficiency.

### Important existing decisions

Treat the following as the baseline until repository evidence establishes a newer approved decision:

- VAH/VAL remain useful candidates.
- Tick-pressure and volume-bin features are diagnostic/experimental unless demonstrated to improve out-of-sample performance.
- Do not enable an experimental feature merely because it has been implemented.
- Preserve bounded data structures wherever mathematically appropriate.
- Cumulative volume profiles may require different retention rules from rolling features.

### External order-flow integration

Investigate the existing external-data architecture.

Where Sierra Chart/Denali or genuine CME/COMEX data is available, integrate only the compact normalized external context required by AMIGO.

Do not unnecessarily export or duplicate massive raw exchange datasets.

The external context should carry, where supported:

- Instrument identity.
- Source.
- Timestamp.
- Sequence or version.
- Data quality.
- Age.
- Heartbeat.
- Staleness status.
- Relevant normalized market features.

Stale, malformed, disconnected or mismatched external data must fail closed.

If the external source is unavailable, AMIGO must correctly identify the degraded data quality rather than pretending that proxy data is equivalent.

Do not make paid services or exchange subscriptions a prerequisite for basic system operation.

---

# 8. NEWS, MACROECONOMICS AND POINT-IN-TIME DATA

This is a critical system component.

Audit all existing news, macroeconomic, calendar, sentiment and external-context services.

The objective is to create a reliable, timestamp-correct external information layer.

## 8.1 News infrastructure

Inspect:
- News ingestion.
- Provider connections.
- Economic calendars.
- Event classification.
- Currency and instrument relevance.
- Impact classification.
- Historical datasets.
- Event timestamps.
- Data revisions.
- Duplicate handling.
- Time-zone conversions.
- Release-time accuracy.
- Market-session alignment.

For XAUUSD, investigate relevant information including:

- Federal Reserve decisions.
- Inflation releases.
- Employment data.
- Treasury yields.
- US dollar conditions.
- Central-bank communication.
- Geopolitical events where reliable structured data is available.

Do not indiscriminately treat every global headline as relevant to gold.

## 8.2 Point-in-time integrity

A critical requirement is that historical decisions must only use information available at the historical decision timestamp.

For every news or macro record, investigate whether the dataset provides:

- Event identifier.
- Event time.
- Publication time.
- First-available time.
- Revision time, where applicable.
- Original value.
- Revised value.
- Previous value.
- Forecast value.
- Source.
- Currency.
- Impact.
- Event category.

Where historical publication vintages are available, preserve them.

Do not substitute the latest revised value into a historical decision where that value was not known at the time.

This would create look-ahead bias.

## 8.3 Download missing datasets

You are authorised to research and download relevant publicly accessible historical datasets where needed.

Prioritise:

- Official central-bank and government datasets.
- Official economic-release archives.
- Reputable financial-data research repositories.
- Academic research datasets.
- Legitimate historical economic-calendar datasets.
- Publicly available market datasets with documented timestamps.

For example, investigate relevant FRED, ALFRED, Federal Reserve, BLS, BEA and other official data sources where appropriate.

Do not assume that a dataset has point-in-time integrity simply because it contains historical dates.

Check its methodology.

Do not bypass paywalls, licensing restrictions, access controls or API restrictions.

If an essential dataset is unavailable or lacks reliable historical vintages, explicitly identify the limitation and implement an honest degraded-data policy.

## 8.4 Macro integration

Investigate the relationship between gold and:

- DXY or an appropriate dollar proxy.
- US Treasury yields.
- Real yields.
- Inflation expectations.
- Interest-rate expectations.
- Relevant central-bank policy information.

Avoid naive correlation assumptions.

Investigate:
- Time-varying relationships.
- Lag structures.
- Regime dependence.
- Structural breaks.
- Multicollinearity.
- Data publication delays.
- Incremental predictive information.

Macro features must not automatically become trade triggers.

Their value must be demonstrated through incremental out-of-sample testing.

## 8.5 News safety

NEWS must be handled as a market-state and risk-context feature.

Investigate:
- Pre-event risk.
- Event-window risk.
- Post-event volatility.
- Spread expansion.
- Slippage.
- Abnormal price movement.
- Data uncertainty.

Do not blindly block every economic event or trade every high-impact release.

The resulting policy must be explicit, tested and configurable.

---

# 9. RISK ENGINE — ABSOLUTE PRIORITY

Risk correctness takes precedence over signal frequency.

Audit all calculations, broker specifications, sizing logic and execution constraints.

The intended risk architecture includes:

- Account-aware risk calculation.
- Equity/balance handling as specified by existing configuration.
- Risk-per-trade calculation.
- Stop-distance validation.
- Tick-value and tick-size handling.
- Contract-size validation.
- Volume minimum and step handling.
- Margin feasibility.
- Symbol-specific calculations.
- Broker execution constraints.
- Minimum-lot risk rejection.
- Exposure aggregation where supported.

### Existing risk principles

Preserve the following unless demonstrably superseded by an explicitly approved decision:

1. The micro-account distortion mechanism must remain bounded.
2. Maximum micro-account risk distortion is 5× the configured risk, not unlimited.
3. Distortion should decrease monotonically as account size increases.
4. Do not introduce a maximum-drawdown component into the risk curve.
5. A minimum lot that exceeds permitted risk must not be forced into execution.
6. MIN_LOT_EXCEEDS_RISK / MIN_LOT_UNSAFE must result in a safe rejection.
7. Leverage must not be mistaken for reduced market risk.
8. Stop adaptation must remain deterministic and independently testable.
9. ONNX must not silently become the authority for adaptive stop-loss decisions.

### Mathematics audit

Independently derive and verify:

- Monetary risk.
- Stop-loss monetary exposure.
- Lot-size calculation.
- Tick-value conversion.
- Currency conversion.
- Volume-step rounding.
- Risk distortion.
- Maximum permitted exposure.
- Margin requirements.
- Portfolio exposure where applicable.

Use independent calculations and broker specification fixtures.

Investigate any discrepancies between OrderCalcProfit, OrderCalcMargin and the internal calculations.

Resolve warnings and unsafe assumptions, including existing OrderCalcProfit-related issues where they remain present.

Never silently round volume upward if doing so exceeds the risk limit.

### Mandatory risk tests

Test:
- Extremely small accounts.
- Micro accounts.
- Larger accounts.
- Different leverage levels.
- Different contract specifications.
- Different tick values.
- Different stop distances.
- Different account currencies.
- Minimum lot greater than target risk.
- Invalid symbol information.
- Missing tick values.
- Zero or invalid equity.
- Margin insufficiency.
- Floating-point boundaries.

A system that cannot trade safely under a given broker constraint must return NO_TRADE.

It must never manufacture an opportunity by exceeding the permitted risk.

---

# 10. EXECUTION AND MQL5 CORE

The MQL5 implementation is the final trading authority.

Audit:
- AMIGO.mq5.
- All `.mqh` include files.
- Signal generation.
- Feature construction.
- Regime engine.
- Strategy engine.
- Risk engine.
- Execution engine.
- Trade management.
- Stop-loss and take-profit calculations.
- Break-even logic.
- Trailing stops.
- Position ownership.
- Magic numbers.
- Symbol selection.
- Account validation.
- Error handling.
- Duplicate-order prevention.
- Decision identifiers.
- State persistence.

Preserve the existing DecisionResult and TradeIntent contracts where they remain valid.

The decision identifier, signal identifier and idempotency key must remain consistent with the established contract.

Verify that the action classifications remain coherent:

- TRADE.
- REDUCE.
- WAIT.
- NO_TRADE.

Verify the data-quality classifications:

- TRUE.
- PROXY.
- LIMITED.
- MISSING.

Verify that the system cannot accidentally interpret missing or stale external information as a valid trading signal.

### Stop management

Inspect the existing deterministic stop-adaptation and trailing mechanisms.

The established trailing concept is activation after break-even, followed by trailing based on 25% of favourable movement from entry, subject to the actual approved implementation and configuration.

Verify the arithmetic, broker constraints, state transitions and restart behaviour.

Do not replace working stop logic with a more complicated model without evidence.

### ONNX

Treat the existing ONNX model as a future or suspended integration unless repository evidence establishes otherwise.

Do not allow a placeholder model to influence actual decisions.

Do not create a fake machine-learning integration simply to make the architecture appear complete.

---

# 11. EXTERNAL SERVICES AND INTEGRATION

Do not limit your audit to MQL5.

Find every external service that AMIGO depends on or was intended to depend on.

This includes:

- Python services.
- Market-data ingestion.
- News ingestion.
- Economic calendar services.
- Macro-data services.
- External order-flow integration.
- Sierra/Denali integration where configured.
- Local API servers.
- File-based communication.
- Named pipes or sockets.
- Background processes.
- Scheduled tasks.
- Configuration and environment variables.
- Logging and monitoring.
- Dataset update processes.
- Any external scripts or dependencies.

Create a dependency map.

For each service, determine:

1. What it does.
2. Whether it is actually implemented.
3. Whether it runs.
4. Whether its output is consumed.
5. Whether its output is correct.
6. Whether its timestamps are reliable.
7. Whether its failure is handled safely.
8. Whether its resource consumption is acceptable.
9. Whether the service duplicates functionality already present elsewhere.
10. Whether it provides measurable value.

### Integration requirements

All services must have clearly defined data contracts.

Validate:
- Schema.
- Instrument identity.
- Timestamp.
- Data quality.
- Freshness.
- Sequence.
- Version compatibility.
- Heartbeat.
- Error state.
- Account identity where applicable.

Reject malformed, stale, mismatched or incomplete messages.

Do not permit an external service to bypass the MQL5 risk engine or directly place trades.

MT5 remains the final authority for broker feasibility, risk and execution.

### Multiple accounts

Inspect whether the existing architecture supports independent operation across two Exness accounts.

Where configured, each account must have isolated:

- Trading state.
- Positions.
- Orders.
- Magic-number ownership.
- Account identity.
- External-context routing.
- Execution decisions.

Do not allow one account's state to contaminate another account's decision-making.

Do not invent account mappings or login identifiers.

If a required account mapping is missing, identify it as a manual configuration requirement.

---

# 12. MATHEMATICAL AND ACADEMIC RESEARCH

You are expressly authorised to revise the mathematics of AMIGO.

However, every significant revision must be supported by credible research.

Do not rely on unsupported claims, trading-industry marketing material or arbitrary optimisation.

### Research sources

Prioritise:

1. Peer-reviewed academic journals.
2. Published financial econometrics research.
3. Established market microstructure research.
4. Working papers from reputable institutions.
5. Official exchange documentation.
6. Official data-provider methodology.
7. Reproducible research repositories.
8. Established open-source implementations with inspectable code.

Where useful, investigate papers and work relating to:

- Market microstructure.
- Price discovery.
- Order-flow imbalance.
- Volume imbalance.
- Market impact.
- Multi-timeframe analysis.
- Regime-switching models.
- Bayesian inference.
- Volatility estimation.
- Mean reversion.
- Trend persistence.
- Information theory.
- Point-in-time financial data.
- Backtest bias.
- Transaction costs.
- Optimal execution.
- Risk management.

### Every proposed improvement must contain

- Research reference.
- Author and publication.
- Publication year.
- DOI or official URL where available.
- Relevant mathematical concept.
- Why it is relevant to AMIGO.
- What existing limitation it addresses.
- Proposed implementation.
- Computational cost.
- Expected benefit.
- Potential failure modes.
- Validation method.

Where research scripts or reproducible implementations are available, inspect them.

Do not blindly copy code from research repositories.

Verify licensing, assumptions, dependencies and compatibility.

### Evidence hierarchy

Distinguish:

A. Theoretical justification.

B. Empirical evidence from external research.

C. Evidence from AMIGO's own historical data.

D. Out-of-sample validation.

E. Live-market evidence, which remains unavailable until I manually execute the terminal testing stage.

Never describe theoretical plausibility as a proven trading edge.

---

# 13. BACKTESTING AND VALIDATION

Build or repair the existing testing infrastructure rather than creating unnecessary duplicate frameworks.

The objective is to establish whether improvements actually improve the system.

### Required testing

- Unit testing.
- Integration testing.
- Regression testing.
- Historical replay.
- Multi-timeframe validation.
- Chronological validation.
- Point-in-time news validation.
- Risk stress testing.
- Broker specification testing.
- External-service failure testing.
- Restart and state-recovery testing.
- Dual-account isolation testing where supported.
- MQL5 compilation.
- Native-versus-independent calculation comparisons.

### Statistical integrity

Investigate and control:

- Look-ahead bias.
- Survivorship bias.
- Data leakage.
- Selection bias.
- Overfitting.
- Multiple-testing problems.
- Regime dependence.
- Transaction costs.
- Spread.
- Commission.
- Slippage.
- Execution delays.
- Historical data quality.
- Sample-size limitations.

Use chronological training, validation and testing.

Where appropriate, use walk-forward analysis and purged or embargoed validation to reduce leakage from overlapping observations.

Do not repeatedly tune parameters against the final test set.

### Performance measurements

Evaluate:
- Net expectancy.
- Profit factor.
- Win rate.
- Average win/loss.
- Maximum drawdown as an evaluation metric, not a new component of the risk curve.
- Risk-adjusted return.
- Trade frequency.
- Exposure.
- Return distribution.
- Tail losses.
- Regime-specific performance.
- Horizon-specific performance.
- Instrument-specific performance.
- Performance after realistic trading costs.

Do not optimise for win rate alone.

Do not claim profitability based on a small or selectively chosen sample.

### Feature ablation

Test whether each major feature contributes incremental value.

Compare:
- Baseline system.
- Baseline plus multi-timeframe integration.
- Baseline plus value-area features.
- Baseline plus order-flow proxies.
- Baseline plus macro context.
- Baseline plus PIT news.
- Combined system.

Do not assume that combining individually promising features produces a better system.

Remove or disable features that introduce complexity without measurable benefit.

---

# 14. HARDWARE AND COMPUTATIONAL EFFICIENCY

The system must remain practical on my available hardware.

The primary development environment has limited resources, including a Windows laptop with approximately 4 GB RAM, an older Intel i3 processor and an HDD.

Do not design around high-end workstations.

Optimise for:
- Low memory consumption.
- Bounded queues.
- Efficient rolling calculations.
- Incremental feature updates.
- Minimal repeated computation.
- Lightweight background services.
- Efficient file operations.
- Controlled logging.
- Low CPU utilisation.
- Efficient dataset storage.
- Minimal simultaneous processes.

Avoid:
- Unnecessary containers.
- Heavy databases when lightweight storage is sufficient.
- Multiple redundant Python environments.
- Unnecessary machine-learning frameworks.
- Constant full-history recalculation.
- Unbounded tick or footprint storage.
- Large model downloads without a demonstrated need.

Use profiling before optimising.

If a heavier service genuinely improves the system, establish its resource requirements and provide a practical alternative.

---

# 15. SECURITY, RECOVERY AND CONFIGURATION

Inspect all configuration and credentials handling.

Do not expose API keys, passwords, broker credentials or account identifiers in logs, commits or reports.

Do not hardcode secrets.

Use environment variables or appropriate local configuration mechanisms.

Do not modify broker account settings.

Do not change live terminal configurations.

Do not install untrusted executables or execute downloaded binaries without verifying their origin and integrity.

For dependencies:
- Prefer established packages.
- Inspect compatibility.
- Pin versions where appropriate.
- Avoid unnecessary dependencies.
- Record installation requirements.

Maintain recoverability.

Before modifying a major component:
1. Inspect it.
2. Identify dependencies.
3. Establish its existing behaviour.
4. Record the baseline.
5. Make the smallest necessary change.
6. Run relevant tests.
7. Check for regressions.

Never use destructive cleanup as a substitute for diagnosing a problem.

---

# 16. AUTONOMOUS ENGINEERING LOOP

This is the most important operational instruction.

You must work in an iterative engineering loop.

Do not stop after producing an audit report.

Do not stop after fixing the first set of errors.

Do not stop when the code merely compiles.

Continue until the defined completion criteria are satisfied or a genuine external/manual blocker is reached.

## LOOP

### PHASE A — DISCOVER

- Locate AMIGO.
- Identify the authoritative repository.
- Inspect Git history and project documentation.
- Inventory all files and services.
- Map the complete architecture.
- Identify original requirements.
- Identify current implementation status.

### PHASE B — AUDIT

For every component:

- Identify intended behaviour.
- Inspect actual implementation.
- Trace inputs and outputs.
- Inspect dependencies.
- Run existing tests.
- Identify defects.
- Identify missing functionality.
- Identify unsupported assumptions.
- Identify performance problems.
- Identify security and reliability issues.

Produce a prioritised defect register.

### PHASE C — RESEARCH

For every significant theoretical or mathematical defect:

- Find credible research.
- Examine mathematical assumptions.
- Inspect reproducible scripts where available.
- Compare alternative methods.
- Estimate implementation cost.
- Determine whether the proposed improvement is worthwhile.

Do not research endlessly.

Research must lead to an engineering decision.

### PHASE D — DESIGN

Choose the simplest technically correct solution.

For each change, record:

- Problem.
- Evidence.
- Root cause.
- Proposed fix.
- Files affected.
- Dependencies.
- Expected result.
- Test required.
- Rollback method.

### PHASE E — IMPLEMENT

Implement the approved engineering improvements.

Work in dependency order.

Prioritise:
1. Critical trading and risk defects.
2. Incorrect mathematical calculations.
3. Broken data contracts.
4. MQL5 core functionality.
5. Multi-timeframe integration.
6. External services.
7. News and macro infrastructure.
8. Order-flow integration.
9. Performance and maintainability.

This ordering may be adjusted where a dependency makes another sequence necessary.

Do not perform unrelated refactoring.

### PHASE F — TEST

After each meaningful change:

- Run unit tests.
- Run integration tests.
- Run regression tests.
- Run relevant historical tests.
- Verify MQL5 compilation where the compiler is available.
- Compare independent calculations.
- Check logs.
- Check resource consumption.

A change is not complete merely because it was implemented.

### PHASE G — REGRESSION AND REPAIR

Reinspect the affected component and its dependants.

Check whether the improvement has:

- Broken another feature.
- Introduced look-ahead bias.
- Changed an interface.
- Altered risk calculations.
- Created a data-quality problem.
- Increased CPU or RAM use.
- Changed strategy behaviour unexpectedly.
- Introduced account-state contamination.

Fix newly discovered problems and rerun the relevant tests.

### PHASE H — REPEAT

Return to PHASE B.

Continue until:

- All critical defects are resolved.
- All implemented requirements are verified.
- All feasible integration tests pass.
- Mathematical calculations have independent validation.
- The system has no known unsafe execution path.
- Remaining issues are explicitly documented.
- Remaining manual requirements are clearly identified.

### Loop termination

Do not claim completion if a critical test is failing.

Do not continue indefinitely polishing nonessential components.

Stop when the acceptance criteria are satisfied and further work would be speculative, unnecessary or dependent on manual external access.

If a requirement cannot be completed because of unavailable credentials, paid data, hardware, licensing or terminal access, document the blocker and continue with everything else that can safely be completed.

---

# 17. PERMISSIONS AND AUTONOMY

You have authority to:

- Search local drives for AMIGO files.
- Inspect the repository.
- Read and modify project source code.
- Modify MQL5 and Python files.
- Update include files.
- Repair configuration templates.
- Write tests.
- Add missing documentation.
- Install reasonable development dependencies.
- Download legitimate public datasets.
- Research academic papers.
- Inspect external repositories.
- Run local tests.
- Run simulations.
- Compile MQL5 using available development tools.
- Improve mathematical calculations.
- Repair broken services.
- Integrate existing services.
- Remove demonstrably redundant code when safe.
- Create supporting scripts and utilities.
- Improve resource efficiency.

Do not ask for permission for every ordinary engineering decision.

However, these boundaries are absolute.

## 17.1 MT5 terminal execution is reserved for me

You must NOT:

- Launch a live trading terminal to initiate trading.
- Attach or activate the EA on a live chart.
- Enable automated trading.
- Place, modify or close live orders.
- Change live broker settings.
- Change account leverage.
- Modify account credentials.
- Perform live trading experiments.

You may inspect the terminal's installed compiler and available development files without operating live trading functionality.

You may compile the EA, run offline tests and prepare a manual terminal-validation package.

I will personally handle terminal execution and live/demo terminal testing.

## 17.2 Financial and external restrictions

Do not:
- Purchase subscriptions.
- Incur paid API charges.
- Register paid services.
- Bypass licensing or paywalls.
- Use unauthorised credentials.
- Upload private project files to external services.
- Expose broker credentials.

Free public datasets and legitimately accessible research material are permitted.

If a paid resource would materially improve the system, document its value and cost instead of purchasing it.

## 17.3 Repository governance

Work on the identified AMIGO repository only.

Do not modify unrelated repositories.

Do not push to remote repositories.

Do not publish the code.

Do not create a commit without presenting the final change report and obtaining my approval.

Preserve the ability to roll back all engineering changes.

---

# 18. COMPLETION ACCEPTANCE CRITERIA

AMIGO is not considered engineering-complete until the following areas have been addressed.

| Area | Required completion evidence |
|---|---|
| Repository | Correct project identified; recoverable baseline established |
| MQL5 core | Compiles without errors |
| Include files | Interfaces and dependencies validated |
| Regime engine | Regime calculations and transitions tested |
| Strategy engine | Both original strategies function correctly |
| Timeframes | D1–M1 integration verified |
| Trading horizons | Scalping, intraday and swing logic evaluated |
| Risk | Independent calculations and boundary tests pass |
| Execution | Safe decision and execution contracts verified offline |
| Stops | SL, TP, break-even and trailing calculations tested |
| Order flow | TRUE and PROXY sources correctly distinguished |
| External services | Contracts, freshness and failure behaviour verified |
| News | Historical ingestion and PIT integrity tested |
| Macro | Data availability and incremental value evaluated |
| Historical testing | Chronological and cost-aware validation completed |
| Multi-account | Isolation verified where account configuration permits |
| Hardware | Resource consumption measured and acceptable |
| Security | No exposed credentials or unsafe external execution |
| Documentation | Architecture, configuration and manual steps documented |

A feature that is deliberately disabled because it lacks evidence is not automatically a defect.

An implemented but untested feature must not be marked complete.

A Python test passing does not establish native MQL5 parity.

A successful compilation does not establish profitability.

A successful historical backtest does not establish live-market performance.

---

# 19. FINAL DELIVERABLES

At the end of the engineering process, produce the following.

## A. Executive engineering report

Explain:
- What was found.
- What was broken.
- What was missing.
- What was repaired.
- What was improved.
- What was removed or disabled.
- What remains unresolved.

## B. Architecture report

Provide the actual final architecture:

- MQL5 EA.
- Include files.
- Strategy and regime modules.
- Risk and execution.
- Python services.
- External integrations.
- Data providers.
- News and macro infrastructure.
- Historical datasets.
- Testing infrastructure.

Show how information travels through the complete system.

## C. Research report

For significant mathematical changes, provide:

- Academic references.
- URLs and DOIs.
- Mathematical assumptions.
- Previous versus revised approach.
- Why the revision is justified.
- Test results.
- Limitations.

## D. Changed-files report

For every changed file:

- File path.
- Purpose.
- Defect addressed.
- Change implemented.
- Tests performed.

Also list newly created files and deleted or disabled functionality.

## E. Testing report

Show:
- Tests executed.
- Tests passed.
- Tests failed.
- Tests unavailable.
- MQL5 compiler results.
- Independent mathematical comparisons.
- Historical validation.
- Regression results.
- Resource measurements.

Never invent test results.

## F. External services report

List every external dependency, its purpose, installation status, configuration requirements, health-check procedure and remaining limitations.

## G. Dataset report

For every acquired dataset:

- Source.
- Licence.
- Date range.
- Frequency.
- Timestamp convention.
- Revision/vintage availability.
- Quality assessment.
- Storage location.
- Update procedure.

## H. Manual terminal execution package

Prepare a clear procedure for my manual testing.

Include:
- Required files.
- Required configurations.
- Compiler/build instructions.
- MT5 installation location requirements.
- Symbol configuration.
- Account-specific checks.
- Shadow/demo test procedure.
- Expected logs.
- Expected NO_TRADE conditions.
- Expected successful decision behaviour.
- Failure conditions requiring immediate suspension.

Do not execute this stage yourself.

## I. Remaining issues

Classify every remaining issue as:

- NOT SPECIFIED.
- REQUIRES MANUAL CONFIGURATION.
- EXTERNAL DEPENDENCY.
- ENGINEERING GAP.
- CONFLICT.
- EXPERIMENTAL / UNPROVEN.
- VERIFIED.

Explain what is needed to resolve each one.

## J. Final engineering status

Provide an honest completion percentage by component, with the evidence supporting each percentage.

Do not use a single inflated overall percentage to conceal incomplete critical functionality.

---

# 20. FINAL INSTRUCTION

You are being entrusted with the engineering completion of an existing trading system.

Be rigorous, practical and sceptical.

Challenge weak mathematics.

Challenge unsupported trading assumptions.

Challenge unnecessary complexity.

Use research to improve the theoretical foundation, but do not confuse academic sophistication with economic value.

Preserve the original AMIGO vision while correcting implementation weaknesses.

Integrate the full D1–M1 timeframe hierarchy into the existing trading horizons.

Make all external services, datasets, Python components and MQL5 modules work together where technically feasible.

Prioritise correct risk calculations and safe failure behaviour over generating more trades.

Do not stop at an audit.

Do not stop at a successful compilation.

Do not stop after fixing one subsystem.

Run the complete engineering loop, validate the interactions between components, fix regressions and repeat.

**The goal is not to make AMIGO look sophisticated. The goal is to make AMIGO function correctly, efficiently, reliably and with the strongest defensible trading edge that the available data and evidence can support.**

Begin with repository discovery and baseline inspection.

Do not modify files until you have established the authoritative AMIGO repository and its recoverable baseline.

Then proceed autonomously through the engineering loop.

I will personally handle all MT5 terminal execution and final live/demo operational testing.
