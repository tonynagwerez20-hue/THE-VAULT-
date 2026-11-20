# THE-VAULT / AlgoMind

The Vault is the collaboration home for AlgoMind and its AMIGO XAUUSD system.

## Start here

- `Amigo/` — small Python package entry points.
- `MQL5/` — MT5 expert, includes, scripts, and broker-facing execution code.
- `Python/` — research, bridge, data, feature, risk, and test code.
- `research/` — experiments, protocols, datasets, and quantitative evidence.
- `Docs/` — specifications, engineering decisions, audits, and handover notes.
- `reports/` — generated result summaries.
- `schemas/` — contracts shared across MQL5 and Python.
- `config/` — reproducible configuration files.
- `data/` — local or externally sourced data references; do not commit private credentials.
- `scratch/` — disposable investigations; not production authority.

## Authority boundary

MQL5 is the final authority for order submission, hard risk, position management, and transaction reconciliation. Python may provide research and validated external context, but it must not bypass MQL5 safety gates.

## Collaboration rules

1. Work on a topic branch; keep `main` release-ready.
2. Use a pull request for changes to MQL5, risk, bridge, schemas, or research claims.
3. Keep generated logs and scratch output out of production folders.
4. Every quantitative claim must name its data period, costs, sample size, and whether it is native MT5 or offline.
5. Never commit API keys, account credentials, broker tokens, or private tick archives.

## AMIGO flow

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
    K --> L[Risk, sizing, margin, spread, broker checks]
    L --> M[TradeIntent validation]
    M --> N[OrderSend and broker execution]
    N --> O[Journal and reconciliation]
    O -->|confirmed| P[Position management]
    O -->|ambiguous| Q[Admission quarantine]
```
