# EXTERNAL INTELLIGENCE ARCHITECTURE SPECIFICATION
**AlgoMind / ASAP Retail Order-Flow System**
**Date:** September 23, 2026
**Status:** Frozen Data Contract Specification

---

## 1. Principle & Core Boundaries
Python collects, normalizes, and packages external intelligence (CFTC COT, Proxy Options, Macro/Geopolitical Context, and News Calendars) into structured payloads.

MQL5 ingests these payloads via atomic file handshakes. **Python NEVER transmits direct trade execution commands (`BUY` / `SELL`)**. Python publishes context; MQL5 retains final execution authority.

---

## 2. Event Intelligence Data Model
Every external event record must populate the following canonical fields:

```text
event_id                    : String (UUID or hash)
source                      : String (e.g., "CFTC", "CBOE", "BLS", "FED")
source_type                 : String ("GOVERNMENT", "EXCHANGE", "CENTRAL_BANK", "NEWS_FEED")
category                    : String ("CFTC_COT", "OPTIONS_PROXY", "ECONOMIC_NEWS", "FOMC")
country_region              : String ("US", "EZ", "UK", "JP", "GLOBAL")
institution                 : String ("CFTC", "FED", "ECB", "BLS")
asset_relevance             : String ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD")
title                       : String
description                 : String
event_timestamp             : ISO-8601 UTC string
publication_timestamp       : ISO-8601 UTC string
retrieval_timestamp         : ISO-8601 UTC string
available_from_timestamp    : ISO-8601 UTC string (strictly enforced for point-in-time backtesting)
scheduled_unscheduled       : String ("SCHEDULED", "UNSCHEDULED")
market_relevance            : Float (0.0 to 1.0)
data_quality                : String ("TRUE", "PROXY", "LIMITED", "MISSING")
point_in_time_status        : String ("ORIGINAL", "REVISED", "FINAL")
confidence                  : Float (0.0 to 1.0)
expiry_timestamp            : ISO-8601 UTC string
```

---

## 3. Freshness & Stale-Data Fail-Closed Handling
- **CFTC COT Data**: Maximum allowed age = 8 days ($691,200$ seconds). If age exceeds limit, `cftc_valid` becomes `false`.
- **Options Proxy Data**: Maximum allowed age = 24 hours ($86,400$ seconds). If age exceeds limit, `options_valid` becomes `false`.
- **News Events**: Active window evaluated dynamically around scheduled timestamps ($\pm 15$ to $\pm 30$ minutes).
- **Transport Failure**: If file age exceeds 300 seconds, MQL5 sets `DQ_STALE_EXTERNAL` bitmask flag and reverts to purely local MQL5 strategy state.
