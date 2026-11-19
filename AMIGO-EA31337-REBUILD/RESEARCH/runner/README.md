# Working offline research package

Created on E: at `E:\AMIGO-EA31337-REBUILD\research-data\amigo-research-v1`.

This is a working adapter and research replay around the existing Python prototype. It is not a replacement native AMIGO engine and does not claim hedging or multi-horizon parity.

## Data

`dataset.json` selects **111 validated months / 430,794,421 original quotes** from the existing immutable HistData ZIP archives. It is an archive-backed dataset: the runner streams the original compressed files rather than duplicating hundreds of millions of rows. Thirteen problematic months remain excluded. There is no sorting, timestamp correction, deletion of duplicate rows, interpolation or synthetic data. Requests touching an excluded/unavailable month fail explicitly; separate periods must not be joined into a continuous return series.

Provider-documented fixed EST is converted to UTC by adding five hours. Every selected ZIP is SHA-256 checked on use. The three imported prototype source files are also hash checked. Input quotes are checked for finite positive bid/ask and nondecreasing timestamps. This does not certify complete trading-calendar coverage, historical execution liquidity or undocumented clock behavior.

## Account sizes and assumptions

The runner processes the same ticks for **$5, $10, $25, $50, $100, $250, $500, $1,000, $5,000 and $10,000**.

`scenario.json` explicitly identifies assumed standard-contract economics: tick size .01, $1 per tick per lot, .01 minimum/step, $7 round-trip commission per lot, .10 adverse price slippage, and daily swap −$20 long/−$10 short per lot. These are scenario inputs, not verified broker tariffs. The inherited prototype uses fixed 0.5% risk and one position; it does not simulate hedging, margin, the native adaptive risk curve or native horizon exits. No broker or live terminal is connected.

## Run

```powershell
python -B E:\AMIGO-EA31337-REBUILD\research-data\amigo-research-v1\replay.py --start 2016-11-21 --end 2016-11-24 --output E:\AMIGO-EA31337-REBUILD\research-data\amigo-research-v1\research_20161121_24.json
```

Dates are UTC; end is exclusive. Use a new output filename for every run. The runner refuses to replace an existing result. A failed checksum requires investigating the change rather than silently accepting a new source version.

## What actually ran

The UTC day **18 November 2016** was replayed successfully across all ten sizes using **145,670 real bid/ask quotes**. It produced **zero closed trades in every account**. This establishes adapter/runner execution, not profitable trading or full strategy warm-up. The recorded output is `pilot_20161118.json`; do not infer that all positions were closed merely from a zero closed-trade count—each account also records its open position and marked equity.

Additional checks passed: rejection of an excluded October date range; a known 10% running-drawdown fixture; controlled stop execution matching the unmodified prototype; idempotent report generation; and cash/closed/unrealized ledger reconciliation. These are recorded in `research_runner_checks.json` and do not constitute MQL5 parity.

## Memory and reporting

Ticks are parsed in bounded chunks and replayed in batches of 10,000. The wrapper replaces per-tick equity storage with an online peak/drawdown accumulator. It reports final cash balance, marked equity, closed P/L, separate cash adjustments (including swap), unrealized P/L after reserved commission, and an open-position record. No Sharpe or profit-factor claim is generated from incomplete cost attribution. Trade records still grow with the number of completed trades, rather than the number of ticks.

Original AMIGO source and all downloaded archives remain unchanged. The next usable step is a longer **continuous accepted interval** under the same explicit research assumptions. Full native hedge-account results still require the native replay work identified in the audit.
