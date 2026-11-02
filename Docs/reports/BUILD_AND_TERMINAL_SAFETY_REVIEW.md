# AMIGO — Build and Terminal Safety Review

## 1. Safety Directive & Incident History

> [!CAUTION]
> **Strict Operational Boundary**
> An unexpected MetaQuotes demo-account authentication incident previously occurred when MT5 launched with blank account settings, violating network isolation requirements (documented in `FINAL_END_PRODUCT_ACCEPTANCE_REPORT.md` as **BLK-001**).
> 
> Under no circumstances may an agent:
> - Launch `terminal64.exe` or MetaTrader 5 GUI/Strategy Tester.
> - Authenticate any trading account or broker connection.
> - Dispatch real or demo network packets outside the local machine.

## 2. Audit of Build & Execution Scripts

### A. `run_offline_backtest.bat`
```bat
@echo off
...
start "" "C:\Program Files\MetaTrader 5\terminal64.exe" /config:"C:\Users\USER\Desktop\ALGOMIND\test_isolated_bt.ini"
...
```
**Safety Audit Findings**:
1. **Direct Process Execution**: Invokes `terminal64.exe` with a configuration file.
2. **Network Exposure Risk**: `terminal64.exe` is not firewalled by default on Windows. If launched, MT5 can connect to MetaQuotes discovery access points or existing cached servers.
3. **Verdict**: **UNSAFE TO EXECUTE**. Must remain unexecuted until operating system firewall rules enforce strict outbound network blocking on `terminal64.exe`.

### B. `test_isolated_bt.ini`
```ini
[Common]
Login=0
ProxyEnable=0
CertificatesPath=
NewsEnable=0
Server=
```
**Safety Audit Findings**:
1. Setting `Login=0` and leaving `Server=` empty was intended to isolate the terminal.
2. However, MT5's default internal fallback behaviour when launched with empty credentials is to scan for open community access points or prompt demo account creation.
3. **Verdict**: **INSUFFICIENT ISOLATION GUARANTEE**. Configuration file settings alone cannot guarantee TCP/IP silence.

### C. MetaEditor Compilation (`metaeditor64.exe`)
- The compilation commands used:
  ```powershell
  Start-Process -FilePath "C:\Program Files\MetaTrader 5\metaeditor64.exe" -ArgumentList '/compile:...','/log:...' -Wait
  ```
- **Safety Audit Findings**:
  - `metaeditor64.exe` executes purely local file compilation without opening trading ports or authenticating broker sessions.
  - Generates binary `.ex5` files locally.
  - **Verdict**: **SAFE & COMPLIANT**.

### D. File Synchronization
- Copies `.ex5` and `.mqh` files into the terminal's roaming application directory (`AppData\Roaming\MetaQuotes\Terminal\...`).
- Does not start processes, open sockets, or mutate live terminal memory.
- **Verdict**: **SAFE**.
