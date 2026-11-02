# CFTC / COT DATA CONTRACT SPECIFICATION
**AlgoMind / ASAP Retail Order-Flow System**

## 1. Governance & Data Philosophy
CFTC Commitments of Traders (COT) data provides macro positional context. It is **NOT** an intraday execution trigger.

- **Source**: U.S. Commodity Futures Trading Commission (CFTC) Disaggregated / Legacy COT Reports.
- **Instrument**: COMEX Gold (GC - Code 088691).
- **Publication Frequency**: Weekly (Friday 15:30 US/Eastern for Tuesday position snapshots).
- **Strict No-Lookahead Rule**: Historical backtests MUST use `available_from_timestamp` (Friday release time), NOT the Tuesday observation snapshot date.

## 2. Canonical Fields

```text
report_period             : String ("WEEKLY")
publication_timestamp     : ISO-8601 UTC string
available_from_timestamp  : ISO-8601 UTC string
participant_category      : String ("MANAGED_MONEY", "COMMERCIAL_HEDGERS")
long_positions            : Integer
short_positions           : Integer
spreading_positions       : Integer
open_interest             : Integer
net_position              : Integer (Long - Short)
net_change                : Integer (Current Net - Previous Net)
percentile_3yr            : Float (0.0 to 100.0)
extreme_flag              : Boolean (True if percentile <= 10 or >= 90)
data_quality              : String ("TRUE")
```

## 3. EA Scoring Integration
COT context modulates strategy scoring via capped influence ($\pm 0.05$ score modifier):
- Extremely Bullish COT ($\ge 90th$ percentile commercial hedging / money manager shorting): $-0.05$ long modifier (overcrowded long).
- Extremely Bearish COT ($\le 10th$ percentile): $+0.05$ long modifier (extreme short positioning / reversal setup).
