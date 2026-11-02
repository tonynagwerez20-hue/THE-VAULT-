# AMIGO — Horizon Telemetry, Logging & Attribution

## 1. Unified Logging Syntax
Every horizon-aware event emits structured log tags to facilitate real-time monitoring and offline parsing:

```
[Amigo][INFO][POSITION_MGMT] ticket=<pid> horizon=<SCALPING|INTRADAY|SWING> dir=<BUY|SELL> entry=<price> current=<price> tp=<price> be_trigger=<price> be_ratio=<ratio> trail_mode=<mode>
```

When positions are updated or closed:
```
[Amigo][INFO][POSITION_MGMT] ticket=<pid> horizon=<HORIZON> CLOSED reason=<EXIT_REASON> price=<exit_price>
```

## 2. Telemetry Attribution Fields
Telemetry sent to external analytics (and recorded in local logs) captures:
- `decision_id`: Monotonic sequence identifier
- `horizon`: `ENUM_HORIZON` (1=Scalping, 2=Intraday, 3=Swing)
- `regime`: `ENUM_REGIME` classification
- `hypothesis`: `ENUM_HYPOTHESIS` (Continuation vs Mean Reversion)
- `hold_time_seconds`: Total duration from open to close
- `exit_reason`: Expiry, Session Close, SL, TP, or Trailing Stop Hit
