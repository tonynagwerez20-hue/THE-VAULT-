# PHASE 4 RUNTIME TRANSPORT TEST REPORT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Transport Handshake Tests

| Test ID | Test Scenario | Python Action | MQL5 Reaction | Verified Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **TEST 1** | **Valid Message** | Publish `schema_version=100`, fresh timestamp. | `ReadExternalContext` returns `true`; `DQ_OK`. | Context parsed & active in scoring. |
| **TEST 2** | **Stale Message** | Set file modification age to $150\text{s}$ ($> 120\text{s}$). | Sets `DQ_STALE_EXTERNAL`; `cftc_valid=false`. | External modifiers disabled safely. |
| **TEST 3** | **Corrupt Payload**| Inject line `bad_key_without_equals`. | Parser skips line; default values preserved. | Zero crash; default values maintained. |
| **TEST 4** | **Missing File** | Delete `algomind_ext_in.txt`. | Returns `false` (`FILE_OPEN_FAIL`); sets `DQ_EXTERNAL_ABSENT`. | Strategy runs local MQL5 mode only. |
| **TEST 5** | **Duplicate Msg** | Write identical payload twice. | Timestamp matches; no double counting. | Pure functional idempotency verified. |
| **TEST 6** | **Out-of-Order** | Write message with timestamp $< \text{last\_read}$. | Point-in-time check flags staleness. | Out-of-order state rejected safely. |

---

## 2. Conclusion
The atomic key-value file transport (`local_bridge.py` $\leftrightarrow$ `External Context Compactor.mqh`) demonstrates complete fail-closed reliability across all 6 transport failure tests.
