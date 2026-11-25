# THE-VAULT / AlgoMind

The Vault is the collaboration home for AlgoMind and its AMIGO XAUUSD system. The verified rebuild is in `AMIGO_REBUILD_DELIVERY_20261120/`.

## Start here

- `Amigo/` — lightweight Python package entry points.
- `MQL5/` — MT5 expert, includes, scripts, and broker-facing execution code.
- `Python/` — research, bridge, data, feature, risk, and tests.
- `research/` — experiments, protocols, datasets, and quantitative evidence.
- `Docs/` — specifications, engineering decisions, audits, and handover notes.
- `reports/` — generated result summaries.
- `schemas/` — contracts shared across MQL5 and Python.
- `config/` — reproducible configuration files.
- `data/` — local/external data references; never commit credentials.
- `scratch/` — disposable investigations, not production authority.

## Authority boundary

MQL5 is the final authority for order submission, hard risk, position management, and transaction reconciliation. Python may provide research and validated external context, but it must not bypass MQL5 safety gates.


## AMIGO system wiring

```mermaid
flowchart TD
    A[MT5 ticks and bars] --> B[Startup/runtime gates]
    X[Python bridge: CFTC, options, news] --> Y[Validated external payload]
    Y --> B
    B -->|ready| C[Closed M1 decision boundary]
    B -->|blocked| Z[No trade + runtime diagnostic]
    C --> D[Quote-tick replay and TIB]
    C --> E[Snapshot, features, and ATR]
    C --> F[Top-down D1/H4/H1/M30/M15/M5/M1 context]
    D --> G[Regime and strategy arbitration]
    E --> G
    F --> G
    G --> H[Continuation / trend]
    G --> I[Mean reversion / value]
    H --> J[TIB + horizon confirmation]
    I --> J
    J --> K[News and external gate]
    K --> L[Risk: 2% daily stop, sizing, margin, spread, broker checks]
    L -->|rejected| Z
    L --> M[TradeIntent validation]
    M --> N[OrderSend / broker execution]
    N --> O[Journal and reconciliation]
    O -->|confirmed| P[Position management]
    O -->|ambiguous| Q[Admission quarantine]
    Q --> Z
```

The external bridge is disabled during tester/optimization runs to prevent look-ahead data.
