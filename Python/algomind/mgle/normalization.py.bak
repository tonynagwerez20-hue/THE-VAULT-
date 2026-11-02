"""
ALGOMIND MACRO / GEOPOLITICAL / GOLD / PROXY-OPTIONS LAYER (MGLE)
==================================================================
Robust Normalization Engine (v1.0)
Computes point-in-time Median Absolute Deviation (MAD) scaled robust Z-scores.
Does not assume Gaussian distribution. Zero look-ahead bias.
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple

def robust_mad_scale(data: np.ndarray) -> float:
    """Computes MAD_scaled = 1.4826 * median(|x_i - median(x)|)."""
    if len(data) == 0:
        return 1.0
    med = np.median(data)
    mad = np.median(np.abs(data - med))
    scale = 1.4826 * mad
    return scale if scale > 1e-8 else 1.0

def compute_robust_zscore(current_val: float, historical_vals: List[float], clip_val: float = 3.0) -> Tuple[float, float]:
    """
    Calculates robust Z-score: z_t = (x_t - median(x_history)) / MAD_scaled.
    Returns (z_score, mad_scale). Clips only for numerical stability if requested.
    """
    if not historical_vals or len(historical_vals) < 3:
        return (0.0, 1.0)
    
    arr = np.array(historical_vals, dtype=np.float64)
    med = np.median(arr)
    scale = robust_mad_scale(arr)
    
    z = (current_val - med) / scale
    if clip_val > 0.0:
        z = np.clip(z, -clip_val, clip_val)
    return (float(z), float(scale))

def compute_surprise_zscore(actual: float, consensus: Optional[float], historical_surprises: List[float]) -> Optional[float]:
    """
    Calculates normalized economic release surprise: (actual - consensus) / sigma_surprise.
    Returns None (MISSING) if consensus is unavailable.
    """
    if consensus is None or np.isnan(consensus):
        return None
    
    raw_surprise = actual - consensus
    if not historical_surprises or len(historical_surprises) < 3:
        scale = max(abs(consensus) * 0.10, 1.0) # Fallback scale
    else:
        scale = float(np.std(historical_surprises))
        if scale <= 1e-8:
            scale = 1.0
            
    z = raw_surprise / scale
    return float(np.clip(z, -3.0, 3.0))
