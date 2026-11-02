# NEWS AND FOMC RECONCILIATION AUDIT
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026

---

## 1. Multi-Source Reconciliation Protocol
The system reconciles Python external economic calendar data with MT5 terminal native calendar events (`CalendarValueGet` / `CalendarEventGet`).

- **Reconciliation Engine**: `news_reconciliation_engine.py`
- **Matching Tolerance**: Scheduled timestamp within $\pm 300$ seconds and matching country code.

---

## 2. Reconciled State Inventory

| State Name | Conditions | Strategy Action | Fail-Closed Policy |
| :--- | :--- | :--- | :--- |
| **`MATCHED`** | Python and MT5 events match scheduled time and values. | Normal Event Processing | Allowed |
| **`PYTHON_ONLY`** | Event present only in Python calendar feed. | Logged & Caution Applied | Allowed with warning |
| **`MT5_ONLY`** | Event present only in MT5 terminal calendar. | Logged & Caution Applied | Allowed with warning |
| **`CONFLICT`** | Actual value or timestamp mismatch between sources. | Blackout / Veto | **`NO_TRADE` Gate Active** |
| **`UNCONFIRMED`** | Actual value pending or release incomplete. | Blackout / Veto | **`NO_TRADE` Gate Active** |
| **`RELEASE_CONFIRMED`**| Actual value released and matched without conflict. | Proceed to Event Reaction | Allowed |

---

## 3. FOMC Document Distinction
FOMC Minutes releases are maintained as distinct document-based events separate from rate decisions or CPI releases. Hawkish/Dovish sentiment scores act as contextual modifiers and never generate automated trades without price/delta confirmation.
