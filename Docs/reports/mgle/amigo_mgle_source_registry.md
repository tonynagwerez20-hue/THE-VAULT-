# Amigo Mgle Source Registry

## 1. Overview
Authoritative documentation report for Amigo MGLE layer: Amigo_mgle_source_registry.md.

## 2. Technical Specification & Verification
- Enforces Point-In-Time causality (publication_timestamp <= T).
- Data quality explicitly tagged (TRUE for primary sources, PROXY for options/orderflow estimates).
- Operates strictly in SHADOW MODE (Zero impact on frozen MQL5 decision rules & hard risk).

## 3. Status
**VERIFIED & FULLY FUNCTIONAL**

