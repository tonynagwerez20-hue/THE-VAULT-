---
name: amigo-quant-validation
description: Qualify AMIGO historical data and evaluate native account and horizon backtests with explicit execution assumptions, independent accounting, held-out research and reproducible evidence.
---

# Quantitative validation

Read [the operating contract](../amigo-redesign-loop/references/contract.md) and [acceptance gates](../amigo-redesign-loop/references/acceptance.md). Do not optimize or certify an engine before its causal/execution behavior is established. A correct negative result is useful; a profitable invalid run is not.

## Data qualification

Keep source archives immutable. Record provider URL/date, hashes, schema, price scale, timestamp precision/timezone and actual coverage. Check bid/ask validity, reversals, equal-time observations, duplicate rows, gaps, session/calendar breaks and warm-up. A monthly file's existence is not complete coverage. Preserve observation ordering and availability time.

Never silently sort disorder, reinterpret DST, delete duplicate ticks, synthesize gaps or substitute candles for a tick-dependent strategy. Distinct quotes sharing a timestamp are legitimate possibilities. Duplicate removal can alter imbalance and observation counts. A repair needs independent provenance, a versioned derived dataset, exact transformation and source-row mapping; otherwise quarantine or acquire verifiable replacement data. Different providers are not interchangeable without a declared comparability experiment.

Use E: for large assets and bounded-memory reads. Verify imported native data and logs for generated fallback ticks. Mark quote-direction delta/footprint/DOM/VWAP as PROXY, not exchange trades or actual depth. Historical fillability, queue position and liquidity are absent from bid/ask files unless independently supplied.

## Freeze the experiment

Before examining performance, record strategy/code version, parameters, data window, warm-up, account grid, horizons, costs, exclusions, development/validation/held-out partition and intended acceptance questions. Record all trials and changes to prevent choosing only successful runs. If the full requested window is unavailable, state the exact shorter scope; do not join disconnected periods into a continuous equity curve.

Run the approved ten equity sizes independently. Keep account denomination, contract scale, leverage, hedge margin, costs and currency conversion explicit. If broker history is unavailable, distinguish hypothetical scenario/sensitivity results from verified broker economics. Zero trades require admission/warm-up reasons, not an automatic conclusion that risk is correct. Never relax policy to force a USD 5 account to trade.

Require separate supported-horizon diagnostics and the real combined arbitration run. Preserve horizon identity through exits. Do not present the existing one-position Python prototype as native AMIGO. Quantify actual agreement/differences on identical inputs where parity is claimed.

## Independent accounting

Rebuild balance from confirmed fills, costs and cash adjustments; reconcile every position and daily baseline. Reconcile marked equity separately, with explicit final marking versus liquidation and exit-cost treatment. Allocate commission/swap to trades before reporting net win/loss, expectancy or profit factor. Treat open trades, partial exits, no-trade/no-loss cases and deposits consistently.

Check reported net/gross P/L, drawdown, RR, holding/exposure, trade frequency and tail losses against the ledger. Daily stop percent and total-period max drawdown are different measures. For Sharpe/Sortino/Calmar use a stated return definition, time sampling, annualization and risk-free assumption; irregular ticks are not equally spaced daily returns. If required inputs are missing, do not invent the metric.

## Robustness

After software acceptance, run held-out/rolling evaluations, account/horizon/regime breakdowns and plausible spread, slippage, delay, commission and financing stress. Use sensitivity neighborhoods justified by the strategy, not an enormous blind search. Report instability and trade-count limitations. For bootstrap/Monte Carlo choose a resampling scheme that respects serial dependence and distinguish trade-order, return and execution simulations. State assumptions; no unsupported confidence claims or arbitrary passing Sharpe thresholds.

Guard against look-ahead, training/test overlap, selection/multiple-testing bias and reuse of the holdout after parameter decisions. If a parameter is changed after seeing held-out results, that period has become development evidence. Do not extrapolate a short positive sample into a decade or future guarantee.

Deliver reproducible run manifests and commands, source/data/binary hashes, full trade/day ledgers, account/horizon comparison, cost attribution, metrics definitions, missing-data/native-parity limitations and a P0–P3 findings register. Name the tests actually executed and distinguish native assertions, reference tests, source checks and economic experiments. Give one scoped readiness verdict and the next narrow task.
