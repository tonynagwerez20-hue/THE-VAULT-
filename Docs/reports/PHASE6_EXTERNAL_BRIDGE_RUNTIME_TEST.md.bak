# PHASE 6 — EXTERNAL BRIDGE RUNTIME TEST REPORT

**Document Status**: Authoritative Engineering Audit  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  

---

## 1. External Bridge Architecture

The external bridge transfers intelligence asynchronously between Python and MQL5 via atomic file exchange:
- **Inbox (Python $\rightarrow$ MQL5)**: `MQL5\Files\algomind_ext_in.txt`
- **Outbox (MQL5 $\rightarrow$ Python)**: `MQL5\Files\algomind_mkt_out.txt`
- **Freshness Gate**: `InpStaleThresholdSec = 120` seconds.

---

## 2. Tested Scenarios & Verified Runtime Outcomes

| Test Scenario | Test Payload / Condition | Expected EA Result | Verified Log Result | Fail-Closed Status |
| :--- | :--- | :--- | :--- | :--- |
| **1. Fresh Valid File** | Valid KV pairs, age < 120s | Accepted, `DQ_STALE` unset | `ReadExternalContext` returns `true` | PASS |
| **2. Stale Context File** | File age > 120s | `DQ_STALE_EXTERNAL` set | `DQ_STALE_EXTERNAL` flag active | PASS (`ACTION_NO_TRADE`) |
| **3. Missing File** | File deleted / absent | `DQ_EXTERNAL_ABSENT` set | Logs `FILE_OPEN_FAIL` | PASS (`ACTION_NO_TRADE`) |
| **4. Corrupted Format** | Malformed KV pairs | Parse failure $\rightarrow$ zero struct | Safe fallback to default | PASS (`ACTION_NO_TRADE`) |
| **5. Timestamp Regress** | Older timestamp written | Ignore older state | `g_ext.timestamp` unchanged | PASS |

---

## 3. Bridge Verification Summary

The external bridge is **IMPLEMENTED AND VERIFIED** in the live MT5 environment. `ReadExternalContext()` executes every 5 seconds inside `OnTick()`, correctly updates `g_ext`, and triggers `DQ_STALE_EXTERNAL` whenever file updates cease.
