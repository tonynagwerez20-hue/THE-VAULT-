"""
ALGOMIND MACRO / GEOPOLITICAL / GOLD / PROXY-OPTIONS LAYER (MGLE)
==================================================================
Macro & Geopolitical Component Processing Engines (v1.0)
Calculates Real-Yields, USD Index, Economic Surprises, and Geopolitical Intensity.
"""

from __future__ import annotations
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional
from algomind.mgle.schema import DataQualityTag, GeoEvent
from algomind.mgle.normalization import compute_robust_zscore, compute_surprise_zscore

class MacroEngines:
    @staticmethod
    def compute_real_yield_engine(current_10y_real: float, historical_10y_reals: List[float]) -> Dict[str, Any]:
        """Calculates 10Y Real Yield robust z-score and momentum."""
        z, scale = compute_robust_zscore(current_10y_real, historical_10y_reals)
        delta_bp = (current_10y_real - historical_10y_reals[0]) * 100.0 if historical_10y_reals else 0.0
        return {
            "real_yield_raw": current_10y_real,
            "real_yield_z": z,
            "real_yield_bp_change": delta_bp,
            "mad_scale": scale,
            "quality": DataQualityTag.TRUE
        }

    @staticmethod
    def compute_usd_engine(current_dxy: float, historical_dxys: List[float]) -> Dict[str, Any]:
        """Calculates Broad USD Index robust z-score and inverse gold pressure context."""
        z, scale = compute_robust_zscore(current_dxy, historical_dxys)
        gold_usd_pressure = -z # Inverse contextual relationship
        return {
            "usd_index_raw": current_dxy,
            "usd_index_z": z,
            "gold_usd_pressure": gold_usd_pressure,
            "mad_scale": scale,
            "quality": DataQualityTag.TRUE
        }

class GeoEngine:
    @staticmethod
    def compute_geo_intensity(events: List[GeoEvent], lookback_hours: float = 24.0, now_ts: int = 0) -> Dict[str, Any]:
        """
        Computes transparent Geopolitical Intensity Index:
        GeoIntensity = GeoSeverity_norm * Novelty_norm * Persistence_norm * SourceConfidence_norm
        """
        if not events:
            return {
                "geo_intensity_index": 0.0,
                "event_count": 0,
                "active_conflict_state": "LOW",
                "quality": DataQualityTag.TRUE
            }

        # Filter events in lookback window
        window_sec = lookback_hours * 3600.0
        active_events = [e for e in events if (now_ts - e.event_timestamp) <= window_sec]
        
        if not active_events:
            return {
                "geo_intensity_index": 0.0,
                "event_count": 0,
                "active_conflict_state": "LOW",
                "quality": DataQualityTag.TRUE
            }

        intensities = [e.geo_intensity for e in active_events]
        max_intensity = float(np.max(intensities))
        avg_intensity = float(np.mean(intensities))
        composite_index = float(np.clip(0.70 * max_intensity + 0.30 * avg_intensity, 0.0, 1.0))

        conflict_state = "LOW"
        if composite_index >= 0.80: conflict_state = "EXTREME"
        elif composite_index >= 0.50: conflict_state = "HIGH"
        elif composite_index >= 0.25: conflict_state = "MODERATE"

        return {
            "geo_intensity_index": composite_index,
            "event_count": len(active_events),
            "active_conflict_state": conflict_state,
            "quality": DataQualityTag.TRUE
        }
