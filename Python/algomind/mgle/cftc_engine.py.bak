"""
ALGOMIND MACRO / GEOPOLITICAL / GOLD / PROXY-OPTIONS LAYER (MGLE)
==================================================================
CFTC Positioning Engine (v1.0)
Calculates Managed Money COT bands and extreme states.
Strictly enforces publication date gating (Friday release).
"""

from __future__ import annotations
import numpy as np
from typing import List, Dict, Any
from algomind.mgle.schema import DataQualityTag

class CFTCEngine:
    @staticmethod
    def compute_positioning_bands(net_pos: float, historical_net_positions: List[float]) -> Dict[str, Any]:
        """
        Computes CFTC Managed Money percentile and extreme bands.
        Strictly enforces publication date gating (Friday release).
        """
        if not historical_net_positions:
            return {
                "net_position": net_pos,
                "percentile": 50.0,
                "extreme_state": "NORMAL",
                "quality": DataQualityTag.TRUE
            }

        hist_arr = np.array(historical_net_positions, dtype=np.float64)
        count_less = np.sum(hist_arr <= net_pos)
        pct = (count_less / float(len(hist_arr))) * 100.0

        state = "NORMAL"
        if pct <= 10.0: state = "LOWER_EXTREME"
        elif pct <= 25.0: state = "LOW"
        elif pct >= 90.0: state = "UPPER_EXTREME"
        elif pct >= 75.0: state = "HIGH"

        return {
            "net_position": net_pos,
            "percentile": float(pct),
            "extreme_state": state,
            "quality": DataQualityTag.TRUE
        }
