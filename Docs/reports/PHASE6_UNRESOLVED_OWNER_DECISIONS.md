# PHASE 6 — UNRESOLVED OWNER DECISIONS

**Document Status**: Authoritative Governance Register  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  

---

## 1. Governance Decision Register

The following quantitative, architectural, and operational decisions remain open for explicit owner resolution. Default research baselines remain active in code.

| Decision ID | Description | Default Baseline | Options | Status |
| :--- | :--- | :--- | :--- | :--- |
| **DEC-001** | Footprint Price Bin Size | `$0.01` for XAUUSD | `$0.01`, `$0.05`, `$0.10` | Default Active |
| **DEC-002** | Cumulative Delta Reset Scope | `SESSION` | `SESSION`, `ROLLING_50`, `EVENT` | Default Active |
| **DEC-003** | News Blackout Window | 15m pre / 30m post | Dynamic ATR vs Static | Default Active |
| **DEC-004** | Legacy Delta Retirement Timeline | Keep Legacy Delta Active | Retire Legacy vs Keep Dual | Default Active |
| **DEC-005** | Cumulative Delta Scoring Integration | Disconnected (Shadow Only) | Connect vs Shadow Only | Default Active |
| **DEC-006** | Micro-Account Min-Lot Risk Policy | Hard Cap (Reject if lot > risk) | Strict Cap vs Max Distortion | Default Active |
| **DEC-007** | Live Trading Promotion Authorization | `NOT AUTHORIZED` | Shadow Only vs Live Authorized | Default Active |

---

## 2. Policy Enforcement

All open decisions remain locked at their **Default Baseline**. No strategy thresholds or scoring formulas have been modified during Phase 6.
