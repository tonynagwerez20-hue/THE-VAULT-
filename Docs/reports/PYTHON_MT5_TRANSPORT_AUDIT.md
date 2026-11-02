# PYTHON â†” MT5 TRANSPORT AND STATE DELIVERY AUDIT
**Amigo / ASAP Retail Order-Flow System**
**Date:** September 23, 2026
**Status:** Audit & Integration Verification

---

## 1. Transport Mechanism Identification
- **Transport Mechanism**: Atomic Key-Value ANSI File Exchange (per D4 REQ-030 / P-10).
- **ZeroMQ / Sockets**: Deferred (Not active in live code).
- **Files Utilized**:
  - `Amigo_ext_in.txt`: External Context file written atomically by Python (`_atomic_write` using `.tmp` and `os.replace`), read by MQL5 (`ReadExternalContext`).
  - `Amigo_mkt_out.txt`: Market Snapshot written by MQL5 (`WriteSnapshotForExternal`), read by Python (`read_market_snapshot`).

---

## 2. End-to-End Pipeline & Data Handshake Sequence

```text
External Data Sources (CFTC, GLD Options, Economic Calendars)
                        â”‚
                        â–¼
   Python `ExternalContext` Serializer (`to_kv_lines()`)
                        â”‚
                        â–¼
  Atomic File Handoff (`Amigo_ext_in.txt.tmp` âž” `Amigo_ext_in.txt`)
                        â”‚
                        â–¼
   MQL5 `ReadExternalContext()` Parser (Shared-read, ANSI Text)
                        â”‚
                        â–¼
   Schema & Freshness Validation (`Amigo_SCHEMA_VERSION = 100`, Age â‰¤ 120s)
                        â”‚
                        â–¼
   MQL5 Strategy & Regime Scoring Engine (`EvaluateRegime`, `ScoreStrategies`)
                        â”‚
                        â–¼
   Hard Risk Veto & Execution Authority Gate (`Decide`, `CheckRiskLimits`)
```

---

## 3. Fail-Closed & Error Condition Analysis

| Failure Condition | Python Reaction | MQL5 Reaction | Status Label |
| :--- | :--- | :--- | :--- |
| **Python Process Terminated** | File updates cease. | Age > 120s $\rightarrow$ `DQ_STALE_EXTERNAL` flag set, `cftc_valid` & `options_valid` set `false`. | `IMPLEMENTED AND VERIFIED` |
| **File Lock / Partial Write** | `_atomic_write` uses temp file + `os.replace`. | Reader sees complete file or previous complete file; zero partial reads. | `IMPLEMENTED AND VERIFIED` |
| **Schema Mismatch** | Python emits current `SCHEMA_VERSION`. | MQL5 checks `ctx.schema_version != 100` $\rightarrow$ sets `DQ_SCHEMA_MISMATCH`. | `IMPLEMENTED AND VERIFIED` |
| **Future Timestamp** | Python timestamps ISO-8601 UTC. | MQL5 checks `ctx.timestamp > TimeCurrent()` $\rightarrow$ sets `DQ_STALE_EXTERNAL`. | `IMPLEMENTED AND VERIFIED` |
| **Corrupted Payload / Malformed KV** | Ignored by line splitter. | Unrecognized key lines skipped; default field values maintained safely. | `IMPLEMENTED AND VERIFIED` |
| **ZeroMQ / Socket Transport** | N/A | Not implemented. File IPC is sole transport. | `NOT IMPLEMENTED` |

