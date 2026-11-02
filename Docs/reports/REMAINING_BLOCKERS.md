# REMAINING BLOCKERS REGISTER & ENFORCEMENT GAP ANALYSIS
**Project**: AMIGO Core Engine  
**Release Readiness Gate**: `NOT BACKTEST-READY`  
**Current Enforcement Status**: `BLOCKED_BY_ENFORCEMENT_GAP`  
**Date**: 2026-11-02  

---

### Master Blocker Inventory

| Blocker ID | Domain | Classification | Description | Resolving Action | Offline Resolvable? | Priority |
|---|---|---|---|---|:---:|:---:|
| **BLK-001** | Terminal Isolation | `BLOCKED` | Native MT5 terminal unexpectedly authenticated a MetaQuotes demo account in a prior test. Preventive sandbox controls are not yet established. | Implement independent OS-level network isolation (e.g. Windows Firewall rule or isolated container blocking outbound sockets for `terminal64.exe`). | Yes | P0 |
| **BLK-002** | State Rollback Parity | `IMPLEMENTED-UNVERIFIED` | Python prototype proves state rollback on feature assembly failure. Native MQL5 caller rollback under live tick interruption is implemented in code but requires dedicated fault-injection harness. | Run MQL5 fault-injection test script in isolated non-authenticating MT5 runner. | Yes | P1 |
| **BLK-003** | Durable Restart Recovery | `IMPLEMENTED-UNVERIFIED` | Prototype demonstrates duplicate opportunity rejection and ambiguous recovery. Native file-based ledger commit across process restarts needs offline verification. | Construct offline file-based transaction ledger test for MQL5 recovery state. | Yes | P1 |
| **BLK-004** | Calendar & Feed Coverage | `UNVERIFIED` | Symbol-specific session boundaries, broker holidays, and feed coverage cannot be proven from static files alone. | Document authoritative broker trading calendar specifications without live credentials. | Yes | P2 |

---

### Detailed Analysis of Blocker BLK-001 (Terminal Isolation)
* **Observed Incident**: A previous automated test launched the MetaTrader 5 terminal process under assumed "portable" mode. The terminal automatically opened a network connection and registered a MetaQuotes demo account.
* **Why Detection is Insufficient**: The governance charter explicitly states that *detecting an unexpected connection after the fact is a safety failure*. Preventive controls must guarantee that no packet can leave the process boundary before the process is spawned.
* **Required Engineering Remedy**:
  1. Windows Filtering Platform (WFP) / Windows Advanced Firewall blocking rule specifically targeting the executable path `C:\Program Files\MetaTrader 5\terminal64.exe` (Outbound Action = Block).
  2. Running the terminal inside a fully decoupled Windows Sandbox / isolated VM without virtual network adapters.
  3. Pre-flight verification checking that socket calls return `WSAEACCES` or fail closed.

---

### Current Milestone & Readiness Verdict
* **Bridge Defect**: **RESOLVED** (Verified by 7/7 tests in `test_offline_contracts.py`).
* **Multi-Timeframe Architecture**: **RESOLVED** (Verified by 98/98 unit tests and 0-error MQL5 compilation).
* **Overall Release Gate**: **`BLOCKED_BY_ENFORCEMENT_GAP`** (Maintained due to BLK-001).
* **Backtest Readiness**: **`NOT BACKTEST-READY`**.
