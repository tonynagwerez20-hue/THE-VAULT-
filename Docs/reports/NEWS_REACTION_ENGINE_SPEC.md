# NEWS REACTION ENGINE SPECIFICATION
**AlgoMind / ASAP Retail Order-Flow System**

## 1. Engine State Machine
The news reaction system operates as a deterministic 12-state machine:

```text
1.  EVENT_UNKNOWN
2.  EVENT_SCHEDULED
3.  EVENT_APPROACHING           (Within 15 minutes of scheduled release)
4.  EVENT_RELEASE_DETECTED       (First price/spread anomaly or timestamp arrival)
5.  RELEASE_UNCONFIRMED         (Python & MT5 calendars disagree or data pending)
6.  INITIAL_REACTION            (0 to 60 seconds post-release)
7.  REACTION_CONFIRMATION       (1 to 5 minutes post-release)
8.  FOLLOW_THROUGH              (5 to 15 minutes post-release)
9.  REVERSAL_OR_FAILURE         (Failed follow-through or rejection)
10. POST_EVENT_STABILIZATION    (15 to 30 minutes post-release)
11. EVENT_EXPIRED               (Normal market state resumed)
12. NO_TRADE                    (Blackout / unconfirmed data veto)
```

## 2. Multi-Source Calendar Reconciliation
Python external economic calendar and MT5 terminal economic calendar are reconciled on every cycle:

| Python Status | MT5 Calendar Status | Reconciliation Outcome | Action |
| :--- | :--- | :--- | :--- |
| Event Matched | Event Matched | `MATCHED` | Proceed to Evaluate Surprise |
| Python Only | Not in MT5 | `PYTHON_ONLY` | Log & Apply Caution |
| Not in Python | MT5 Only | `MT5_ONLY` | Log & Apply Caution |
| Conflict (Actual/Timestamp)| Conflict | `UNCONFIRMED` / `CONFLICT` | Blackout / `NO_TRADE` Gate |

## 3. ATR-Based Event Reaction Metrics
For every verified event release, measure:
1. **Pre-Event ATR Baseline**: 14-period M5 ATR calculated strictly prior to `EVENT_APPROACHING`.
2. **Initial Displacement**: $\text{Disp}_{1m} = \frac{|P_{t+1m} - P_{\text{pre}}|}{\text{ATR}_{\text{pre}}}$.
3. **5-Minute Follow-Through**: $\text{Disp}_{5m} = \frac{|P_{t+5m} - P_{\text{pre}}|}{\text{ATR}_{\text{pre}}}$.
4. **Spread Expansion**: $\text{SpreadRatio} = \frac{\text{Spread}_{\text{release}}}{\text{Spread}_{\text{pre}}}$.
5. **Delta Reaction**: Footprint delta accumulation during initial 1m and 5m bars.
