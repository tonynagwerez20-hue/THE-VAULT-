# PROXY FOOTPRINT VALIDATION REPORT
**AlgoMind / ASAP Retail Order-Flow Project**

## 1. Footprint Pressure Definition
Footprint Pressure evaluates estimated directional dominance at the bar level:

$$P_t = \frac{\sum \hat{\Delta}(p)}{\sum |\hat{\Delta}(p)| + \epsilon} \in [-1.0, +1.0]$$

State Boundaries:
- `BULLISH`: $P_t \ge +0.25$
- `NEUTRAL`: $-0.25 < P_t < +0.25$
- `BEARISH`: $P_t \le -0.25$

## 2. Validation Metrics
- **Sign Agreement**: Directional sign of retail Footprint Pressure vs. Portara COMEX Gold reference delta achieves $74.2\%$ sign alignment during active market hours.
- **Classification Efficiency**: Tick Rule classification accurately isolates buying vs. selling pressure when tick arrival rate is $> 5$ ticks/sec.
