# PHASE 5 — RUNTIME EVIDENCE REPORT

**Document Status**: Authoritative Engineering Audit  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  
**Environment**: Windows 10, MetaTrader 5 (Terminal PID 7964), MQL5, Python 3.11  
**Operating Mode**: SHADOW ONLY — NO LIVE TRADING  
**Level 3 Status**: LEVEL 3 UNVERIFIED — MT5 RUNTIME RE-ATTACHMENT PENDING  
**Level 4 Status**: NOT AUTHORIZED  

---

## 1. Executive Summary

This report documents the empirical runtime verification state of the AlgoMind / ASAP Retail Order-Flow System for Phase 5.

While the new MQL5 order-flow modules (`AM_*.mqh`) and `InpShadowOnly = true` safety gate were successfully wired into `AMIGO.mq5` and compiled cleanly (0 errors, `AMIGO.ex5` 86,210 bytes deployed), the active MetaTrader 5 GUI process (`terminal64.exe` PID 7964) attached to `XAUUSD, M5` was last initialized at `00:05:23.845` on 2026-09-24 and has not yet reloaded the updated binary.

Per Phase 5 Governance Rule 2.1 (No Invention) and Rule 16 (MT5 GUI Control Limit), **no runtime claim is fabricated**. The system remains **LEVEL 3 UNVERIFIED** until the owner re-attaches the updated `AMIGO.ex5` in MT5 and exports the resulting log artifacts.

---

## 2. Environment & Repository Baseline Inventory

| Property | Value / Hash |
| :--- | :--- |
| **Repository Path** | `C:\Users\USER\Desktop\ALGOMIND` |
| **Git Branch** | `main` |
| **Git Commit** | `19806e4d3dad747d5c428ee05cf707a6e1f42bf2` |
| **MetaEditor Path** | `C:\Program Files\MetaTrader 5\metaeditor64.exe` |
| **Terminal Path** | `C:\Program Files\MetaTrader 5\terminal64.exe` (PID 7964 active) |
| **Terminal Data Dir** | `C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075` |
| **Symbol Display** | `XAUUSD` |
| **Timeframe** | `PERIOD_M5` (5 minutes) |
| **Account / Server** | `Exness-MT5Trial` (Demo / Practice Account) |

### Baseline SHA-256 File Hashes

```
Algorithm SHA256                                                          File
--------- ------                                                          ----
SHA256    4EB17177172144AC4926AE5046B6F739214B3CB67145EF5D794BD93070DD6E57  AMIGO.mq5
SHA256    4BCD1726C76086DBBC34590206C1BA59A75F47BB19078E87958C01AA5EFD7D4D  Strategy Engine.mqh
SHA256    451880E5DF6DC113FC913655E48382483074522E8BBDEFC8B627F1A53656A005  Regime Engine.mqh
SHA256    A88D5487286F35ED42CFC5493CCFA5BD7F415060CBDA63AE3D14A9E3F5444FE5  Risk Engine.mqh
SHA256    014D06E2983B3C606B58A54C05BC5E5DC5F4DFBDE298B2B0E539E0C9CA3ECCFB  Contracts.mqh
SHA256    2379476EDFCB6EFA3ABE68342D6004687AAF8E83FBF7911CF7758A677CD75F73  Execution Engine.mqh
SHA256    B815AD363C607F92DF419736F4B981DC1632D47E1581E23C1832AEA38E3528A6  Configuration.mqh
SHA256    DD52B9994AA45525EE707C34C4F837CDF2DD04D433D7710CB0248C27627F10A5  AM_Footprint.mqh
SHA256    811552AE059A476B21EF4112E819DF2E4A804D3BB43B950B03AEA542DBBE636C  AM_ProxyVWAP.mqh
SHA256    602911B8E8DFFAF71C58268C81428FCBC1E7CC351BE4226B26316AE8CE621588  AM_ActivityProfile.mqh
SHA256    1C47D6B3EEC4B6B292C50DB26E4AB1F6EF21BBCC92CEC818E832F574EFAE013F  AM_FlowPressure.mqh
SHA256    4E86ED91142BB6E2A4B07A8E1C3C4D7A57535437E30EA53A22A90617070564ED  AM_FlowEvents.mqh
```

---

## 3. Evidence Matrix

| Component | Source Implementation | Compilation Status | Live MT5 Log Trace | Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Shadow Execution Gate (`InpShadowOnly`)** | `Execution Engine.mqh` L137 | 0 Errors | Pending EA Reload | `IMPLEMENTED BUT UNVERIFIED AT RUNTIME` |
| **Proxy VWAP (`CAM_ProxyVWAP`)** | `AMIGO.mq5` L99, L237, L317 | 0 Errors | Pending EA Reload | `IMPLEMENTED BUT UNVERIFIED AT RUNTIME` |
| **Proxy Footprint (`CAM_Footprint`)** | `AMIGO.mq5` L100, L236, L296 | 0 Errors | Pending EA Reload | `IMPLEMENTED BUT UNVERIFIED AT RUNTIME` |
| **Activity Profile (`CAM_ActivityProfile`)**| `AMIGO.mq5` L101, L299, L318 | 0 Errors | Pending EA Reload | `IMPLEMENTED BUT UNVERIFIED AT RUNTIME` |
| **Flow Pressure (`CAM_FlowPressure`)** | `AMIGO.mq5` L102, L301, L302 | 0 Errors | Pending EA Reload | `IMPLEMENTED BUT UNVERIFIED AT RUNTIME` |
| **Flow Events (`CAM_FlowEvents`)** | `AMIGO.mq5` L103, L312 | 0 Errors | Pending EA Reload | `IMPLEMENTED BUT UNVERIFIED AT RUNTIME` |
| **External Bridge Transport** | `External Context Compactor.mqh` | 0 Errors | Active (`ReadExternalContext`) | `IMPLEMENTED AND VERIFIED` |
| **Legacy Strategy Scoring** | `Strategy Engine.mqh` | 0 Errors | Active (`[DECISION]`, `[DIAG]`) | `IMPLEMENTED AND VERIFIED` |
