# PHASE 5 — UNRESOLVED OWNER DECISIONS

**Document Status**: Authoritative Governance Register  
**Date**: 24 September 2026  
**System**: AlgoMind / ASAP Retail Order-Flow System  

---

## 1. Decision Register

The following quantitative, architectural, and operational decisions remain open for owner resolution. Per strict project governance, Antigravity has implemented sensible default baselines for research and shadow observation, but will **NOT** alter authoritative trade execution logic until an owner decision is explicitly recorded.

| Decision ID | Description | Default Baseline | Options Available | Impact Area |
| :--- | :--- | :--- | :--- | :--- |
| **DEC-001** | Footprint Price Bin Size | `$0.01` for XAUUSD | `$0.01`, `$0.05`, `$0.10` | Price Binning & Memory |
| **DEC-002** | Cumulative Delta Reset Scope | `SESSION` | `SESSION`, `ROLLING_50`, `EVENT` | Delta Baseline Accumulation |
| **DEC-003** | News Blackout Window | 15m pre / 30m post | Dynamic ATR vs Static 15m/30m | News Execution Filter |
| **DEC-004** | Legacy Delta Retirement Timeline | Keep Legacy Delta Active | Retire Legacy Delta vs Keep Dual | Strategy Scoring Input |
| **DEC-005** | Cumulative Delta Strategy Scoring Integration | Disconnected (Shadow Only) | Connect to Strategy vs Keep Disconnected | Authoritative Scoring |
| **DEC-006** | Micro-Account Min-Lot Risk Distortion Policy | Hard Cap (Reject if lot > max risk) | Strict Cap vs Max Distortion (5x) | Small Account Risk |
| **DEC-007** | Live Trading Promotion Authorization | `NOT AUTHORIZED` | Shadow Only vs Live Authorized | Execution Authority |

---

## 2. Recommended Action

Keep all decisions at their **Default Baseline** during Phase 5 shadow testing. Record owner decisions as explicit user directives prior to any future Phase 6 optimization or promotion attempt.
