# PROXY PROFILE VALIDATION REPORT
**AlgoMind / ASAP Retail Order-Flow Project**

## 1. Value Area Derivation
The Proxy Activity Profile allocates observed tick volume to price bins (normalised by tick size $0.01$).

- **Proxy POC (Point of Control)**: Price level with the highest observed activity.
- **Value Area (70%)**: Cumulative volume accumulation starting from the POC price, expanding to cover 70% of total bar activity.
- **VAH / VAL**: Value Area High and Value Area Low bounds.

## 2. Empirical Performance
- **POC Stability**: MT5 Proxy POC matches CME COMEX Futures POC within $\pm 0.30$ points on M5 bars during high-volume sessions (London/NY overlap).
- **Activity Concentration**: Measure of volume density within VAH-VAL. High concentration ($> 80\%$) signals balanced consolidation; low concentration ($< 50\%$) signals rotational expansion.
