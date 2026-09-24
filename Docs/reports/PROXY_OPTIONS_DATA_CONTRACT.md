# PROXY OPTIONS DATA CONTRACT SPECIFICATION
**AlgoMind / ASAP Retail Order-Flow System**

## 1. Scope & Proxy Labeling
Options context is derived from GLD ETF proxy options or CBOE Gold volatility indexes.
**Proven Quality Tag**: `PROXY` / `ESTIMATED`. It is NEVER claimed to represent total market-wide institutional options exposure.

## 2. Canonical Fields

```text
underlying_symbol         : String ("GLD" / "GC")
source_venue              : String ("CBOE", "YAHOO_FINANCE_PROXY")
observation_timestamp     : ISO-8601 UTC string
futures_spot_basis        : Float (GC - XAUUSD spot basis point difference)
open_interest_conc        : Float (Ratio of Call/Put OI at key strikes)
nearest_strike_dist_atr   : Float (Distance to high-OI strike in ATR units)
gamma_regime              : Integer (-1 = Short Gamma/High Vol, 0 = Neutral, +1 = Long Gamma/Mean Reversion)
options_source_quality    : String ("PROXY")
```

## 3. Usage Rules
Options metrics act purely as a regime and risk modifier:
- `gamma_regime > 0`: Favors `HYP_MEAN_REVERSION` (pinning around key strikes).
- `gamma_regime < 0`: Favors `HYP_CONTINUATION` / Expansion (volatility expansion expected).
