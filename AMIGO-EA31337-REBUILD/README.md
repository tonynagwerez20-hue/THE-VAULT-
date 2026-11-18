# AMIGO correction and delivery status — 18 November 2026

## Implemented

- Native tick-imbalance bars use the existing threshold of 100. Full closed-interval ticks are read with CopyTicksRange, not just OnTick events. Incomplete/stale TIB observations fail closed. A completed TIB opposing continuation vetoes that existing proposal. The current timeframe, opportunity identity, higher-timeframe, news, risk and execution owners remain in place.
- Repaired the native build's missing intent identity fields, duplicate RiskAllows definition, duplicate local declaration, daily-counter configuration reference and database integer read. An unknown daily counter blocks admission.
- Python baseline no longer throttles risk by high-water drawdown. Its minimum-lot decision also enforces the native 2% absolute exposure ceiling. MVE solves the first crossing of the approved equity-dependent risk curve for the supplied fixed distortion; a separate normal-equity helper uses distortion 1.
- Native initialization requires the approved 2% daily limit and a maximum distortion within 1–5. Minimum configured reward/risk is 2. Live execution remains blocked; non-shadow execution is allowed only inside the Strategy Tester.
- Regime confidence refreshes from current evidence and drops to NO_TRADE when the incumbent no longer clears the threshold.
- Rebuild strategy prototypes now initialize, compile against the actual contract, require complete history, clear stale signal flags, handle all-gain/flat RSI correctly and require explicit regime/quality/risk-owned identity context. Uncalibrated multiple proposals fail closed.
- Python prototype replay no longer imports/connects to MT5 or fabricates random trade outcomes. It requires local ticks and explicit contract/cost/day specifications, sizes in cash-per-tick units, updates strategies on completed TIBs, enters on a later timestamp and resolves stops/targets using bid/ask ticks. It includes gap losses, specified slippage/commission/swap, daily rollover and minimum-lot rejection.

The RSI mean-reversion prototype is labeled a reversal heuristic, not validated pivot divergence. The Python prototype is explicitly **not** a parity implementation of the native baseline. It must not be used to claim native AMIGO performance. Historical five-trade/random-outcome reports remain historical artifacts and are superseded for acceptance purposes.

## Verification actually performed

| Check | Result |
|---|---|
| Native EA before repairs, isolated repository includes | 29 errors, 3 warnings |
| Final native EA after repairs, same isolated includes | 0 errors, 0 warnings |
| StrategyProposalTest compilation | 0 errors, 0 warnings |
| StrategyLifecycleTest compilation | 0 errors, 0 warnings |
| QuantRegression native assertion script compilation | 0 errors, 0 warnings |
| Focused Python regression suite | 24 passed |
| Native assertion runtime | NOT VERIFIED: isolated terminal loaded the script but initialization failed; no result file was produced |

No installed EX5 binary was overwritten. Compilation generated binaries only in the isolated working copy. No live account was opened and no live orders were submitted. Native runtime safety, restart behavior, full native/Python parity and economic robustness are not implied by these compilation/unit results.

## Delivery layout

The original E: repository has no remote. Desktop ALGOMIND's existing remote is `https://github.com/tonynagwerez20-hue/THE-VAULT-.git`; its working tree contains pre-existing edits. Delivery uses an isolated branch based on the remote main commit `a3a487339bd258d07a3a2a9cf8cb4720f9ec32c6`, with the self-contained source package under `AMIGO-EA31337-REBUILD/`. Existing remote root code and Desktop edits are not overwritten. The package contains 55 required source/test files, about 697 KB before documentation. It excludes binaries, accounts, market datasets and unrelated working-tree changes.

Git delivery outcome and the actual commit are recorded separately after push. Local application writes only changed source/test files; original versions are backed up first. Pre-existing E: index entries are not staged or committed.

## Ten-year backtest

Requested source: Dukascopy. Requested interval: 2016-11-18 00:00 UTC through 2026-11-18 00:00 UTC, exclusive endpoint. Existing local Exness samples cover only four isolated months, not this decade.

Public Dukascopy probes encountered timeouts, connection resets and HTTP 503. One earlier 2020 hourly probe succeeded. Alternate-host lookup also failed. The resumable downloader validates BI5 records, records checksums and missing-hour evidence, and blocks the full run if boundary coverage is unavailable. It never replaces missing data with generated ticks.

No ten-year backtest result exists yet. Full coverage, historical cost assumptions and a successfully initialized isolated native tester are still required. MT5 real-tick mode alone is not proof of complete real ticks: MetaQuotes documents that missing minutes can be synthesized. Acceptance therefore requires inspecting coverage and tester logs, not merely selecting Model=4.

References: [Dukascopy historical-data export](https://wiki.dukascopy.com/en/development/data-export/) and [MetaQuotes tester tick behavior](https://www.mql5.com/en/docs/runtime/testing).

## Reproduction

Run `python -B -m pytest -q -p no:cacheprovider Python/test_quant_regression.py` from the packaged rebuild with pytest installed. Disable pytest plugin autoload for the focused run. Compile `AMIGO_BASELINE/MQL5/Experts/AMIGO.mq5` with MetaEditor `/inc:` explicitly pointing to `AMIGO_BASELINE/MQL5`, so ambient terminal includes cannot substitute for repository sources.

Acquire data using `Python/dukascopy_ticks.py --start 2016-11-18 --end 2026-11-18 --cache <E-drive-cache> --manifest <manifest.json>`. Exit code 2 means coverage/download is incomplete and no complete backtest may be claimed. Empty hours still require trading-calendar reconciliation. Paid requester-pays S3 access is not automatically enabled.
