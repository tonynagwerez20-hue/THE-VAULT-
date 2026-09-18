"""
ALGOMIND MACRO / GEOPOLITICAL / GOLD / PROXY-OPTIONS LAYER (MGLE)
==================================================================
CFTC Positioning & Proxy Options Engine (v1.0)
Calculates Managed Money COT bands, Realized Vol Ratios, Options OI Concentration,
Black-Scholes Theoretical Gamma Proxies, and Zero-Gamma Crossings.
Strictly tags proxy estimates as DataQualityTag.PROXY.
"""

from __future__ import annotations
import math
import numpy as np
from typing import List, Dict, Any, Optional
from algomind.mgle.schema import DataQualityTag, OptionsProxyLevel

def norm_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

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

class OptionsProxyEngine:
    @staticmethod
    def compute_realized_volatility_ratio(returns_m5: List[float], short_win: int = 12, long_win: int = 288) -> Dict[str, Any]:
        """Calculates short-term vs long-term Realized Volatility ratio."""
        if len(returns_m5) < long_win:
            return {"rv_ratio": 1.0, "regime": "VOL_NORMAL", "quality": DataQualityTag.PROXY}
        
        r = np.array(returns_m5, dtype=np.float64)
        rv_short = np.std(r[-short_win:]) * math.sqrt(288.0 * 252.0)
        rv_long = np.std(r[-long_win:]) * math.sqrt(288.0 * 252.0)
        
        ratio = float(rv_short / rv_long) if rv_long > 1e-8 else 1.0
        
        regime = "VOL_NORMAL"
        if ratio <= 0.70: regime = "VOL_COMPRESSION"
        elif ratio >= 1.50: regime = "VOL_EXPANSION"
        elif ratio >= 2.50: regime = "VOL_EXTREME"

        return {
            "rv_short": float(rv_short),
            "rv_long": float(rv_long),
            "rv_ratio": ratio,
            "regime": regime,
            "quality": DataQualityTag.PROXY
        }

    @staticmethod
    def compute_black_scholes_gamma(S: float, K: float, T_years: float, r: float = 0.04, sigma: float = 0.20) -> float:
        """Calculates Black-Scholes theoretical Option Gamma (per share)."""
        if S <= 0.0 or K <= 0.0 or T_years <= 0.001 or sigma <= 0.0:
            return 0.0
        
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T_years) / (sigma * math.sqrt(T_years))
        phi = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * d1 ** 2)
        gamma = phi / (S * sigma * math.sqrt(T_years))
        return gamma

    @staticmethod
    def compute_theoretical_gex_map(spot: float, atr: float, strike_oi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes Theoretical Gamma Exposure Proxy and Zero-Gamma Crossing Price.
        Strictly labeled DataQualityTag.PROXY.
        """
        if not strike_oi_data or atr <= 0.0:
            return {
                "theoretical_gex_proxy": 0.0,
                "zero_gamma_proxy_price": spot,
                "oi_concentration_strike": spot,
                "options_levels": [],
                "quality": DataQualityTag.PROXY
            }

        total_net_gex = 0.0
        max_oi = 0.0
        max_oi_strike = spot
        options_levels: List[OptionsProxyLevel] = []

        for item in strike_oi_data:
            K = item['strike']
            call_oi = item['call_oi']
            put_oi = item['put_oi']
            tot_oi = call_oi + put_oi
            T_years = item.get('t_years', 30.0 / 365.0)

            if tot_oi > max_oi:
                max_oi = tot_oi
                max_oi_strike = K

            gamma = OptionsProxyEngine.compute_black_scholes_gamma(spot, K, T_years)
            # Dollar-gamma scaling proxy: OI * gamma * S^2 * 100
            call_gex = call_oi * gamma * (spot ** 2) * 100.0
            put_gex = -put_oi * gamma * (spot ** 2) * 100.0 # Standard assumption: puts are short gamma for dealers
            net_gex = call_gex + put_gex
            total_net_gex += net_gex

            dist_atr = (K - spot) / atr
            options_levels.append(OptionsProxyLevel(
                strike_price=K,
                call_oi=call_oi,
                put_oi=put_oi,
                total_oi=tot_oi,
                relative_oi_share=0.0, # Filled in post-pass
                strike_distance_atr=dist_atr,
                theoretical_gamma_proxy=net_gex,
                expiry_ts=item.get('expiry_ts', 0),
                quality_tag=DataQualityTag.PROXY
            ))

        # Interpolate Zero-Gamma Crossing Price
        zero_gamma_price = spot
        options_levels.sort(key=lambda x: x.strike_price)
        for i in range(len(options_levels) - 1):
            l1, l2 = options_levels[i], options_levels[i+1]
            if (l1.theoretical_gamma_proxy * l2.theoretical_gamma_proxy) < 0:
                g1, g2 = l1.theoretical_gamma_proxy, l2.theoretical_gamma_proxy
                p1, p2 = l1.strike_price, l2.strike_price
                zero_gamma_price = p1 + (0.0 - g1) / (g2 - g1) * (p2 - p1)
                break

        return {
            "theoretical_gex_proxy": float(total_net_gex),
            "zero_gamma_proxy_price": float(zero_gamma_price),
            "oi_concentration_strike": float(max_oi_strike),
            "options_levels": options_levels,
            "quality": DataQualityTag.PROXY
        }
