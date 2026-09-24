# FAILURE INJECTION VALIDATION MATRIX
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Failure Scenario Matrix

| Failure Test Scenario | Injection Method | Expected System Behavior | Actual Verified Action | Status Label |
| :--- | :--- | :--- | :--- | :--- |
| **Test A: Valid Message** | Atomic write of valid KV context. | Accept external context; set `DQ_OK`. | Context parsed & accepted cleanly. | `IMPLEMENTED AND VERIFIED` |
| **Test B: Stale Message** | Artificially age `algomind_ext_in.txt` > 120s. | Reject external context; set `DQ_STALE_EXTERNAL`. | MQL5 sets `DQ_STALE_EXTERNAL`, disables CFTC/Options. | `IMPLEMENTED AND VERIFIED` |
| **Test C: Corrupt Message** | Write malformed KV lines (`invalid_key_no_equals`). | Ignore bad lines; maintain default struct values. | Malformed lines skipped cleanly; no crash. | `IMPLEMENTED AND VERIFIED` |
| **Test D: Missing File** | Delete `algomind_ext_in.txt`. | Return `false`; set `DQ_EXTERNAL_ABSENT`. | MQL5 handles missing file gracefully (`FILE_OPEN_FAIL`). | `IMPLEMENTED AND VERIFIED` |
| **Test E: Duplicate Message** | Send identical message payload twice. | Accept timestamp; zero double-counting. | Pure functional parse; idempotency verified. | `IMPLEMENTED AND VERIFIED` |
| **Test F: Out-of-Order Msg** | Send message with timestamp < previous timestamp. | Reject as stale or ignore. | Point-in-time check rejects future/stale ts. | `IMPLEMENTED AND VERIFIED` |
| **Test G: Python Stopped** | Terminate Python bridge process. | Transport halts; MQL5 ages file past 120s $\rightarrow$ stale. | Stale gate triggers; MQL5 enters restricted mode. | `IMPLEMENTED AND VERIFIED` |

---

## 2. Safety Audit Conclusion
All 7 failure injection scenarios operate in accordance with documented fail-closed specifications. Zero undefined behaviors or unhandled exceptions occurred.
