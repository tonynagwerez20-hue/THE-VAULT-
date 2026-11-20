# AlgoMind / AMIGO

AMIGO is the MQL5-first XAUUSD decision and execution system. The verified rebuild is in `AMIGO_REBUILD_DELIVERY_20261120/`.

## AMIGO system wiring

```mermaid
flowchart TD
    A[MT5 ticks and bars] --> B[Startup/runtime gates]
    X[Python bridge: CFTC, options, news] --> Y[Validated external payload]
    Y --> B
    B -->|ready| C[Closed M1 decision boundary]
    B -->|blocked| Z[No trade + RUNTIME_GATE]
    C --> D[Quote-tick replay]
    D --> E[TIB closed bar]
    C --> F[Market snapshot + features]
    C --> G[Top-down D1/H4/H1/M30/M15/M5/M1 context]
    E --> H[Regime and strategy arbitration]
    F --> H
    G --> H
    H --> I[Continuation / trend]
    H --> J[Mean reversion / value]
    I --> K[TIB + horizon confirmation]
    J --> K
    K -->|opposing TIB or invalid horizon| Z
    K --> L[News and external gate]
    L --> M[Risk: 2% daily stop, sizing, margin, spread, min lot]
    M -->|rejected| Z
    M --> N[TradeIntent validation]
    N --> O[OrderSend / broker execution]
    O --> P[Transaction journal + reconciliation]
    P -->|confirmed| Q[Position manager: stops, partials, trailing]
    P -->|ambiguous| R[Admission quarantine]
    R --> Z
```

MQL5 remains the execution and hard-risk authority. The external bridge is disabled during tester/optimization runs to prevent look-ahead data.
