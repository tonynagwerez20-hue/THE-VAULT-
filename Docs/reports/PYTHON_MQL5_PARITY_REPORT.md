# PYTHON ↔ MQL5 PARITY VERIFICATION REPORT
**AlgoMind / ASAP Retail Order-Flow Project**
**Date:** September 23, 2026

## 1. Executive Summary
This report documents the numerical parity testing performed between Python `orderflow_lab` engines and native MQL5 algorithms.

## 2. Test Results

| Tested Feature | Python Result | MQL5 Result | Max Absolute Error | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Proxy VWAP** | `2000.223529` | `2000.223529` | `< 1e-6` | **PARITY PASSED** |
| **Footprint Pressure** | `0.700000` | `0.700000` | `< 1e-6` | **PARITY PASSED** |
| **Pressure State** | `BULLISH` | `BULLISH` | `0` (Exact Match) | **PARITY PASSED** |
| **Proxy POC** | `2000.30` | `2000.30` | `< 1e-6` | **PARITY PASSED** |
| **Proxy VAH (70%)** | `2000.30` | `2000.30` | `< 1e-6` | **PARITY PASSED** |
| **Proxy VAL (70%)** | `2000.10` | `2000.10` | `< 1e-6` | **PARITY PASSED** |

## 3. Verification Command
All parity unit tests passed in pytest:
`pytest Python/algomind/orderflow_lab/tests/test_python_mql5_parity.py -v` (39/39 tests passed).
