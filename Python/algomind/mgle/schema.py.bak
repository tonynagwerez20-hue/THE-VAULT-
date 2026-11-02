"""
ALGOMIND MACRO / GEOPOLITICAL / GOLD / PROXY-OPTIONS LAYER (MGLE)
==================================================================
Canonical Master Schema & Data Quality Definitions (v1.0)
Strictly enforces Point-in-Time (PIT) causality and provenance tracking.
"""

from __future__ import annotations
from enum import IntEnum, auto
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

# ==============================================================================
# 1. DATA QUALITY & PROVENANCE ENUMS
# ==============================================================================
class DataQualityTag(IntEnum):
    TRUE = 0       # Sourced directly from official primary source (e.g. CFTC, Treasury)
    PROXY = 1      # Derived or reconstructed proxy (e.g. GLD options, tick delta)
    LIMITED = 2    # Partial or low-coverage observation
    MISSING = 3    # Unavailable observation

class DataQualityBitmask(IntEnum):
    OK                     = 0x0000
    MISSING_TICKS          = 0x0001
    STALE_EXTERNAL         = 0x0002
    SCHEMA_MISMATCH        = 0x0004
    BROKER_INVALID         = 0x0008
    EXTERNAL_ABSENT        = 0x0010
    FUTURE_LEAKAGE_DETECTED= 0x0020
    FATAL                  = 0x8000

# ==============================================================================
# 2. CAUSAL POINT-IN-TIME OBSERVATION CONTRACT
# ==============================================================================
@dataclass
class ExternalObservation:
    source_id: str                      # e.g. "CFTC_GOV", "FRED", "FOREXFACTORY", "CBOE"
    dataset_id: str                     # e.g. "COT_GOLD_DISAGGREGATED", "TREASURY_10Y_YIELD"
    series_id: str                      # e.g. "MANAGED_MONEY_NET", "DGS10"
    instrument: str                     # e.g. "XAUUSD", "GOLD_FUTURES", "USD"
    observation_timestamp: int          # Epoch seconds of observation date/period
    publication_timestamp: int          # Epoch seconds when observation became public (PIT)
    retrieval_timestamp: int            # Epoch seconds when retrieved into local DB
    unit: str                           # e.g. "CONTRACTS", "PERCENT", "USD"
    value: float                        # Numerical value
    quality_tag: DataQualityTag = DataQualityTag.TRUE
    revision_version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_available_at(self, query_ts: int) -> bool:
        """Point-in-Time Causality Check: Available only if publication_ts <= query_ts."""
        return self.publication_timestamp <= query_ts

# ==============================================================================
# 3. MACRO & GEOPOLITICAL COMPONENT CONTRACTS
# ==============================================================================
@dataclass
class MacroFeature:
    name: str
    raw_value: float
    normalized_zscore: float
    robust_mad_scale: float
    lookback_window_bars: int
    data_quality: DataQualityTag
    publication_ts: int

@dataclass
class GeoEvent:
    event_id: str
    title: str
    category: str
    country_region: str
    event_timestamp: int
    first_seen_timestamp: int
    source_count: int
    severity_norm: float      # [0.0, 1.0]
    novelty_norm: float       # [0.0, 1.0] (1 - duplicate_weight)
    persistence_norm: float   # [0.0, 1.0]
    confidence_norm: float    # [0.0, 1.0]
    geo_intensity: float      # Severity * Novelty * Persistence * Confidence

@dataclass
class OptionsProxyLevel:
    strike_price: float
    call_oi: float
    put_oi: float
    total_oi: float
    relative_oi_share: float
    strike_distance_atr: float
    theoretical_gamma_proxy: float
    expiry_ts: int
    quality_tag: DataQualityTag = DataQualityTag.PROXY

# ==============================================================================
# 4. SERIOUS MACRO LEVEL CONTRACT & TIMEFRAME DECOMPOSITION
# ==============================================================================
@dataclass
class MacroLevel:
    level_id: str
    parent_level_id: Optional[str]      # Non-null for child levels (H4, H1, M15, M5)
    timeframe: str                      # "MACRO", "H4", "H1", "M15", "M5"
    price_center: float
    upper_bound: float
    lower_bound: float
    source_type: str                    # "WEEKLY_EXTREME", "OPTIONS_OI_CLUSTER", "VWAP_ANCHOR", "CFTC_BAND"
    time_horizon: str                   # "MONTHLY", "WEEKLY", "DAILY", "INTRADAY"
    creation_ts: int
    observation_ts: int
    strength: float                     # [0.0, 1.0] (Evidence magnitude)
    confidence: float                   # [0.0, 1.0] (Evidence reliability)
    age_hours: float
    freshness_factor: float             # exp(-lambda * age_hours)
    retest_count: int                   # Post-creation retests ONLY
    reaction_count: int                 # Post-creation valid reactions ONLY
    quality_tag: DataQualityTag = DataQualityTag.TRUE

# ==============================================================================
# 5. MASTER MGLE SNAPSHOT (SHADOW MODE CONTRACT)
# ==============================================================================
@dataclass
class MGLESnapshot:
    schema_version: int = 100
    timestamp: int = 0                  # Epoch seconds
    symbol: str = "XAUUSD"
    
    # Macro Regimes (-1.0 to +1.0 or Categorical String)
    macro_regime_label: str = "NEUTRAL"
    macro_confidence: float = 0.50
    data_coverage_pct: float = 100.0
    
    # Core Engine Normalized Z-Scores
    real_yield_z: float = 0.0
    usd_index_z: float = 0.0
    cftc_net_percentile: float = 50.0
    cftc_position_extreme: str = "NORMAL" # "LOWER_EXTREME", "LOW", "NORMAL", "HIGH", "UPPER_EXTREME"
    
    # Geo & Volatility Proxies
    geo_intensity_index: float = 0.0
    volatility_ratio_rv: float = 1.0      # RV_short / RV_long
    volatility_regime: str = "VOL_NORMAL" # "VOL_COMPRESSION", "VOL_NORMAL", "VOL_EXPANSION", "VOL_EXTREME"
    
    # Options Proxy Aggregates
    options_oi_concentration: float = 0.0
    theoretical_gex_proxy: float = 0.0
    zero_gamma_proxy_price: float = 0.0
    
    # Active Level Collections
    active_macro_levels: List[MacroLevel] = field(default_factory=list)
    active_options_levels: List[OptionsProxyLevel] = field(default_factory=list)
    
    # Provenance Summary
    data_quality_bitmask: int = DataQualityBitmask.OK
    shadow_mode: bool = True            # MUST REMAIN TRUE
