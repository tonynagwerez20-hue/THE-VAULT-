"""Configuration settings for Order-Flow Validation Lab."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class OrderFlowLabConfig:
    instrument: str = "XAUUSD"
    symbol_suffix_list: list[str] = field(default_factory=lambda: ["XAUUSD", "XAUUSDm", "GC"])
    bin_size_mode: str = "AUTO"  # AUTO | FIXED
    fixed_bin_size: float = 0.50  # Price points per bin for Gold
    classification_method: str = "TICK_RULE"  # TICK_RULE | BID_ASK_QUOTE
    
    # Pressure & Surge Baseline Parameters
    pressure_threshold: float = 0.25      # Proposed baseline +-0.25
    surge_threshold: float = 0.35         # Recalibrated MQL5 baseline 0.35
    persistence_bars: int = 2              # Baseline 2 M5 closes
    value_area_pct: float = 0.70          # Standard 70% Value Area
    alt_value_area_pct: float = 0.68      # Alternative 68% Value Area
    
    # Fusion Weights
    fusion_weight_a: float = 0.50
    fusion_weight_b: float = 0.50
    
    # Data Quality Gates
    stale_seconds: int = 120
