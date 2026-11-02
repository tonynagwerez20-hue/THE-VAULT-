"""
ALGOMIND MACRO / GEOPOLITICAL / GOLD / PROXY-OPTIONS LAYER (MGLE)
==================================================================
Serious Macro Level Engine & Multi-Timeframe Decomposition (v1.0)
Generates ATR-normalized levels, computes evidence strength & confidence,
applies exponential age decay, and decomposes levels into H4/H1/M15/M5 areas.
"""

from __future__ import annotations
import math
import numpy as np
from typing import List, Dict, Any, Optional
from algomind.mgle.schema import MacroLevel, DataQualityTag

class MacroLevelEngine:
    @staticmethod
    def compute_exponential_decay(age_hours: float, time_horizon: str = "WEEKLY") -> float:
        """
        Calculates freshness decay factor: freshness = exp(-lambda * age_hours).
        Lambda is scaled by time horizon (Intraday, Daily, Weekly, Monthly).
        """
        decay_half_lives = {
            "INTRADAY": 12.0,   # 12 hours
            "DAILY": 48.0,      # 2 days
            "WEEKLY": 168.0,    # 7 days
            "MONTHLY": 720.0    # 30 days
        }
        half_life = decay_half_lives.get(time_horizon.upper(), 168.0)
        lam = math.log(2.0) / half_life
        freshness = math.exp(-lam * max(age_hours, 0.0))
        return float(np.clip(freshness, 0.05, 1.0))

    @staticmethod
    def construct_macro_level(
        level_id: str,
        price_center: float,
        zone_width_dollars: float,
        current_price: float,
        atr: float,
        source_type: str,
        time_horizon: str,
        creation_ts: int,
        now_ts: int,
        structural_evidence: float,
        macro_evidence: float,
        options_evidence: float,
        retest_count: int = 0,
        reaction_count: int = 0,
        quality_tag: DataQualityTag = DataQualityTag.TRUE
    ) -> MacroLevel:
        """
        Constructs a serious MacroLevel with ATR-normalized bounds, strength, confidence, and freshness.
        """
        half_width = zone_width_dollars / 2.0
        upper_bound = price_center + half_width
        lower_bound = price_center - half_width

        age_hours = (now_ts - creation_ts) / 3600.0
        freshness = MacroLevelEngine.compute_exponential_decay(age_hours, time_horizon)

        # Strength = Weighted magnitude of structural, macro, and options evidence
        quality_factor = 1.0 if quality_tag == DataQualityTag.TRUE else 0.70
        raw_strength = 0.50 * structural_evidence + 0.30 * macro_evidence + 0.20 * options_evidence
        strength = float(np.clip(raw_strength * quality_factor * freshness, 0.0, 1.0))

        # Confidence = Function of source quality, retest verification, and freshness
        retest_bonus = min(retest_count * 0.10, 0.30)
        raw_confidence = 0.60 * quality_factor + 0.20 * freshness + retest_bonus
        confidence = float(np.clip(raw_confidence, 0.0, 1.0))

        return MacroLevel(
            level_id=level_id,
            parent_level_id=None,
            timeframe="MACRO",
            price_center=price_center,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            source_type=source_type,
            time_horizon=time_horizon,
            creation_ts=creation_ts,
            observation_ts=now_ts,
            strength=strength,
            confidence=confidence,
            age_hours=age_hours,
            freshness_factor=freshness,
            retest_count=retest_count,
            reaction_count=reaction_count,
            quality_tag=quality_tag
        )

    @staticmethod
    def decompose_macro_level(parent: MacroLevel, current_atr: float) -> List[MacroLevel]:
        """
        DECOMPOSES parent MacroLevel into H4, H1, M15, and M5 hierarchy.
        Preserves parent_level_id identity across timeframes.
        """
        tf_scales = {
            "H4": 1.00,
            "H1": 0.60,
            "M15": 0.35,
            "M5": 0.20
        }
        
        children: List[MacroLevel] = []
        for tf, scale in tf_scales.items():
            child_id = f"{parent.level_id}_{tf}"
            half_w = (current_atr * scale) / 2.0
            
            children.append(MacroLevel(
                level_id=child_id,
                parent_level_id=parent.level_id,
                timeframe=tf,
                price_center=parent.price_center,
                upper_bound=parent.price_center + half_w,
                lower_bound=parent.price_center - half_w,
                source_type=parent.source_type,
                time_horizon=parent.time_horizon,
                creation_ts=parent.creation_ts,
                observation_ts=parent.observation_ts,
                strength=parent.strength,
                confidence=parent.confidence,
                age_hours=parent.age_hours,
                freshness_factor=parent.freshness_factor,
                retest_count=parent.retest_count,
                reaction_count=parent.reaction_count,
                quality_tag=parent.quality_tag
            ))
            
        return children
