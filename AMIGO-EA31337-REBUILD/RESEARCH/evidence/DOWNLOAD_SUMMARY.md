# XAUUSD tick download results

Saved original archives to `E:\AMIGO-EA31337-REBUILD\research-data\histdata`.

- Requested interval: 18 November 2016 00:00 UTC to 18 November 2026 00:00 UTC, exclusive endpoint.
- Acquired archives: **124** (121 requested monthly files plus 3 warm-up months).
- Total compressed bytes: **3,301,979,150** (3.302 GB decimal).
- Total original CSV records across all archives, including warm-up and records outside the requested interval: **504,932,597**.
- Quote/order checks passed: **111 archives**. This is not proof of complete market coverage.
- Invalid bid/ask quotes: **0**. Adjacent exact duplicate rows: **234028**. Nonadjacent duplicates were not exhaustively checked.
- Backward timestamp events: **72512**, in 2019-10, 2020-10, 2021-10, 2022-10, 2023-10, 2024-10, 2025-10, 2026-06, 2026-07, 2026-08, 2026-09, 2026-10, 2026-11.
- Latest November archive timestamp as supplied: **20261113 165959000**; fixed-EST conversion per provider documentation: **2026-11-13T21:59:59+00:00**. Provider timestamp semantics are under review because of the observed October reversals.

## Backtest acceptance

**Blocked. No ten-year performance result is reported.** A full scan of all November timestamps confirms the maximum is 13 November 2026 16:59:59 provider time (`histdata_endpoint_check.json`), so the requested endpoint is not covered. Monthly archive availability is not equivalent to complete coverage of the requested end date. The backward records must not be silently sorted or deleted. Up to 20 exact original offending row pairs per affected month are preserved in `histdata_timestamp_anomalies.json`.

The requested equity grid is $5, $10, $25, $50, $100, $250, $500, $1,000, $5,000 and $10,000. Each has eight executed analytical risk scenarios; none has a completed historical hedging-account backtest. See `account_backtest_status.json` and `account_scenario_audit.json`.

The existing Python engine does not reproduce native horizon management or hedging/margin behavior. The attached audit-only instruction prohibits implementing fixes. `MULTI_HORIZON_AUDIT.md` explains the source evidence, 102 passing selected tests and required next steps.

## Provenance

`histdata_acquisition_manifest.json` and `histdata_warmup_manifest.json` record monthly source URLs, SHA-256, byte sizes, rows and endpoint timestamps. A residual `error` on an ultimately `validated` record records an earlier transient retry failure; final `status` controls its validation result. The primary manifest's `complete=false` reflects quality failures even when all files have been acquired.

Original files are unmodified. CRC and hashes establish transport integrity and reproducibility, not independent certification of quote truth or fillability. [HistData documents its format, bid/ask fields and timezone](https://www.histdata.com/f-a-q/). No paid service, account connection or live trade was used.
