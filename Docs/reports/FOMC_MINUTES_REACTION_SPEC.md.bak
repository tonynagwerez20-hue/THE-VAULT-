# FOMC MINUTES REACTION SPECIFICATION
**AlgoMind / ASAP Retail Order-Flow System**

## 1. Document vs. Numerical Event Distinction
Unlike CPI or NFP numbers, FOMC Minutes are document-based textual releases. Python extracts sentiment, policy bias (Hawkish / Dovish), and language shift metrics.

## 2. Text Extraction Provenance
- **Source**: Federal Reserve Board FOMC Minutes Release.
- **Extraction Fields**:
  - `document_id`: Hash of published PDF/HTML text.
  - `publication_timestamp`: ISO-8601 UTC.
  - `hawkish_dovish_index`: Float ($-1.0$ = Extremely Dovish, $+1.0$ = Extremely Hawkish).
  - `ambiguous_language_flag`: Boolean (True if contradictory policy signals exist).
  - `extraction_confidence`: Float ($0.0$ to $1.0$).

## 3. Market Reaction Tracking
Simultaneously measure market responses across instruments:
- `DXY_displacement_atr`
- `US10Y_yield_change_bp`
- `XAUUSD_displacement_atr`
- `XAUUSD_footprint_delta`
- `XAUUSD_cumulative_delta`

If text sentiment conflicts with initial price/delta reaction, the event state becomes `UNCONFIRMED` and trading is restricted until `POST_EVENT_STABILIZATION`.
