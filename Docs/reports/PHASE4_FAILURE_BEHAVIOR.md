# PHASE 4 FAILURE BEHAVIOR AUDIT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Runtime Failure Injection Matrix

| Failure Mode | Expected Action | Actual Behavior | Safety Finding |
| :--- | :--- | :--- | :--- |
| **External File Missing** | Revert to local MQL5 mode; set `DQ_EXTERNAL_ABSENT`. | Returns `FILE_OPEN_FAIL`; sets bitmask safely. | PASS |
| **External File Stale (>120s)**| Disable CFTC/Options modifiers; set `DQ_STALE_EXTERNAL`. | Age check sets `DQ_STALE_EXTERNAL`; disables modifiers. | PASS |
| **External File Corrupt** | Ignore bad lines; maintain safe defaults. | Skips bad KV lines; maintains safe default state. | PASS |
| **News Source Conflict** | Trigger `CONFLICT` state; block trading. | Reconciliation engine returns `CONFLICT` $\rightarrow$ `NO_TRADE`. | PASS |
| **Excessive Spread** | Block trade entry. | Spread gate evaluates `spread > max_spread` $\rightarrow$ Veto. | PASS |
| **Insufficient Margin** | Block trade entry. | `OrderCheck` fails $\rightarrow$ returns `ORDERCHECK_FAIL`. | PASS |
| **Minimum Lot Risk > Max Risk**| Round down to 0; block trade entry. | Risk engine enforces `NO_TRADE` when min lot risk > allowed. | PASS |

---

## 2. Safety Audit Statement
Zero permissive failure leaks identified. Every failure mode enforces fail-closed behavior.
