"""Extended Schema & Data Quality Definitions for Order-Flow Validation Lab.

Strict Provenance Tagging:
- DataQualityTag: TRUE | PROXY | LIMITED | MISSING
- Enforces strict no-invention boundaries.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum


class DataQualityTag(str, Enum):
    TRUE = "TRUE"         # Actual exchange-traded bid/ask/trade data (e.g. Portara COMEX GC)
    PROXY = "PROXY"       # Estimator derived from retail quotes / tick volume (e.g. MT5 tick direction)
    LIMITED = "LIMITED"   # Partial historical sample or OHLCV-only context
    MISSING = "MISSING"   # Data field absent / unpopulated


class PressureState(str, Enum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


@dataclass
class SourceMetadata:
    source_name: str
    instrument: str
    venue: str
    symbol: str
    timezone: str = "UTC"
    start_time: str = ""
    end_time: str = ""
    data_type: str = "TICK"  # TICK | OHLCV | DEPTH
    price_type: str = "SPOT"  # SPOT | FUTURES | SYNTHETIC
    volume_type: str = "TICK_COUNT"  # REAL_VOLUME | TICK_COUNT | ESTIMATED
    bid_available: bool = True
    ask_available: bool = True
    trade_available: bool = False
    depth_available: bool = False
    classification_method: str = "TICK_RULE"
    license_notes: str = "FREE_PUBLIC_ACCESS"
    quality_tag: DataQualityTag = DataQualityTag.PROXY


@dataclass
class OrderFlowTick:
    timestamp: float
    price: float
    bid: float = 0.0
    ask: float = 0.0
    volume: float = 1.0
    tick_volume: int = 1
    direction: int = 0  # +1 = Buy, -1 = Sell, 0 = Neutral
    classified_by: str = "TICK_RULE"  # TICK_RULE | BID_ASK_QUOTE
    quality_tag: DataQualityTag = DataQualityTag.PROXY


@dataclass
class FootprintBin:
    price: float
    observed_activity: float = 0.0
    tick_count: int = 0
    estimated_buy_activity: float = 0.0
    estimated_sell_activity: float = 0.0
    estimated_delta: float = 0.0
    price_response: float = 0.0
    pressure: float = 0.0
    quality_tag: DataQualityTag = DataQualityTag.PROXY


@dataclass
class ProxyFootprintSnapshot:
    timestamp: float
    symbol: str
    timeframe: str = "M5"
    bins: Dict[float, FootprintBin] = field(default_factory=dict)
    total_activity: float = 0.0
    total_buy_activity: float = 0.0
    total_sell_activity: float = 0.0
    total_delta: float = 0.0
    footprint_pressure: float = 0.0
    pressure_state: PressureState = PressureState.NEUTRAL
    is_surge: bool = False
    is_flip: bool = False
    flip_direction: int = 0
    transition_event: str = "NONE"
    quality_tag: DataQualityTag = DataQualityTag.PROXY


@dataclass
class ProxyVWAPSnapshot:
    timestamp: float
    symbol: str
    proxy_vwap: float
    typical_price: float
    vwap_deviation: float  # (Price - VWAP) / (ATR + eps)
    cum_weighted_price: float = 0.0
    cum_activity: float = 0.0
    quality_tag: DataQualityTag = DataQualityTag.PROXY


@dataclass
class ProxyProfileSnapshot:
    timestamp: float
    symbol: str
    poc_price: float
    vah_price: float
    val_price: float
    value_area_pct: float = 0.70
    activity_concentration: float = 0.0
    high_activity_nodes: List[float] = field(default_factory=list)
    low_activity_nodes: List[float] = field(default_factory=list)
    quality_tag: DataQualityTag = DataQualityTag.PROXY


@dataclass
class ProxyDOMRow:
    price: float
    observed_activity: float = 0.0
    est_buy: float = 0.0
    est_sell: float = 0.0
    est_delta: float = 0.0
    tick_count: int = 0
    pressure: float = 0.0
    best_bid: bool = False
    best_ask: bool = False


@dataclass
class ProxyDOMSnapshot:
    timestamp: float
    symbol: str
    best_bid: float = 0.0
    best_ask: float = 0.0
    spread: float = 0.0
    dom_rows: List[ProxyDOMRow] = field(default_factory=list)
    dom_mode: str = "PROXY_ACTIVITY_LADDER"
    quality_tag: DataQualityTag = DataQualityTag.PROXY


@dataclass
class FlowShadowLogEntry:
    timestamp: str
    symbol: str
    current_fusion: float
    footprint_pressure: float
    current_state: str
    footprint_state: str
    current_surge: bool
    footprint_surge: bool
    current_transition: str
    footprint_transition: str
    current_flip: str
    footprint_flip: str
    proxy_vwap: float
    vwap_dev: float
    poc: float
    vah: float
    val: float
    dom_mode: str = "PROXY"
    data_quality: str = "PROXY"

    def to_log_string(self) -> str:
        return (
            f"[FLOW_SHADOW] ts={self.timestamp} sym={self.symbol} "
            f"fus={self.current_fusion:.3f} fp_press={self.footprint_pressure:.3f} "
            f"c_state={self.current_state} fp_state={self.footprint_state} "
            f"c_surge={int(self.current_surge)} fp_surge={int(self.footprint_surge)} "
            f"fp_trans={self.footprint_transition} fp_flip={self.footprint_flip} "
            f"p_vwap={self.proxy_vwap:.3f} vwap_dev={self.vwap_dev:.3f} "
            f"poc={self.poc:.3f} vah={self.vah:.3f} val={self.val:.3f} "
            f"dom={self.dom_mode} dq={self.data_quality}"
        )
