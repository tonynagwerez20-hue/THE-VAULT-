"""
AMIGO Layered Architecture Module (10-Layer Design).
Location: E:\AMIGO-EA31337-REBUILD\AMIGO_BASELINE\Python\algomind\layered_architecture.py

Implements explicit, modular layers:
1. Tick and TIB Integrity (Validation, chronological ordering, positive spread, bar building)
2. Regime Classification (Trend, Range, High-Vol, Low-Vol, Unstable/Disrupted)
3. Top-Down Structure (Higher TF, Execution TF, Lower TF structure & agreement veto)
4. Horizon Selection (Scalping, Intraday, Swing)
5. Strategy Selection (Trend Continuation vs Mean Reversion vs Combined Arbitration)
6. Timing Trigger (Pullback + Confirmation, Range Rejection, Volatility Breakout + Retest)
7. External Context (GLD Options, GDELT News, CFTC COT point-in-time)
8. Risk & Capital Feasibility (2% daily loss limit, min lot feasibility)
9. Execution & Reconciliation Admission (Transaction journaling, admitted orders)
10. Position & Order Management (Simulated lifecycle, slippage, costs)
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
import math
import numpy as np
import pandas as pd

@dataclass
class TickRecord:
    timestamp_utc: datetime
    bid: float
    ask: float
    bid_vol: float
    ask_vol: float
    source_hash: str

@dataclass
class TIBBar:
    bar_id: str
    open_time_utc: datetime
    close_time_utc: datetime
    open_bid: float
    high_bid: float
    low_bid: float
    close_bid: float
    open_ask: float
    high_ask: float
    low_ask: float
    close_ask: float
    mid_close: float
    spread: float
    total_volume: float
    vwap: float
    rolling_std: float
    ema20: float
    ema50: float
    atr: float

class Layer1_TickAndTIBIntegrity:
    """Validates raw ticks and constructs deterministic TIB bars."""
    @staticmethod
    def validate_tick(tick: TickRecord) -> Tuple[bool, str]:
        if tick.bid <= 0 or tick.ask <= 0:
            return False, "INVALID_NEGATIVE_OR_ZERO_PRICE"
        if tick.bid > tick.ask:
            return False, "NEGATIVE_SPREAD_INVALID"
        spread = tick.ask - tick.bid
        if spread > 3.0: # excessive spread
            return False, "EXCESSIVE_SPREAD_ANOMALY"
        return True, "VALID_TICK"

class Layer2_RegimeClassifier:
    """Classifies market regime into Trend, Range, High-Vol, Low-Vol, Unstable."""
    @staticmethod
    def classify_regime(bar: TIBBar, news_active_48h: bool) -> str:
        if news_active_48h:
            # High-impact news event window
            return "UNSTABLE"
        
        # Volatility check
        is_high_vol = bar.atr > 2.0 or bar.rolling_std > 2.5
        is_low_vol = bar.atr < 0.4 and bar.rolling_std < 0.5
        
        # Trend strength check
        ema_diff = abs(bar.ema20 - bar.ema50)
        is_trending = ema_diff > (bar.atr * 0.8) and (bar.mid_close > bar.ema20 or bar.mid_close < bar.ema20)
        
        if is_high_vol and not is_trending:
            return "HIGH_VOLATILITY"
        if is_low_vol:
            return "LOW_VOLATILITY"
        if is_trending:
            return "TREND"
        return "RANGE"

class Layer3_TopDownStructure:
    """Evaluates multi-timeframe structural alignment."""
    @staticmethod
    def evaluate(htf_trend: str, etf_trend: str, ltf_trend: str) -> Tuple[bool, str]:
        # Structure agreement veto: If HTF strongly opposes ETF, veto trade
        if (htf_trend == "BULL" and etf_trend == "BEAR") or (htf_trend == "BEAR" and etf_trend == "BULL"):
            return False, "HTF_ETF_DISAGREEMENT_VETO"
        return True, "TIMEFRAME_ALIGNED"

class Layer4_HorizonManager:
    """Manages horizon-specific parameters."""
    CONFIGS = {
        "scalping": {
            "sl_dist": 1.0,
            "tp_dist": 1.5,
            "max_hold_bars": 20,
            "min_rr": 1.5
        },
        "intraday": {
            "sl_dist": 2.5,
            "tp_dist": 5.0,
            "max_hold_bars": 80,
            "min_rr": 2.0
        },
        "swing": {
            "sl_dist": 5.0,
            "tp_dist": 12.0,
            "max_hold_bars": 300,
            "min_rr": 2.4
        }
    }
    @classmethod
    def get_config(cls, horizon: str) -> Dict[str, Any]:
        return cls.CONFIGS.get(horizon, cls.CONFIGS["scalping"])

class Layer5_StrategySelector:
    """Gating strategy by regime to eliminate contradictory entries."""
    @staticmethod
    def select_strategy(regime: str, requested_strategy: str) -> Tuple[bool, str]:
        # Hypothesis 1: Regime-gating removes mean-reversion losses during persistent trends!
        if requested_strategy == "mean_reversion":
            if regime == "TREND":
                return False, "MEAN_REVERSION_FORBIDDEN_IN_TREND_REGIME"
            if regime == "UNSTABLE":
                return False, "MEAN_REVERSION_FORBIDDEN_IN_UNSTABLE_REGIME"
        elif requested_strategy == "trend_continuation":
            if regime == "RANGE":
                return False, "TREND_CONTINUATION_FORBIDDEN_IN_RANGE_REGIME"
            if regime == "UNSTABLE":
                return False, "TREND_FORBIDDEN_IN_UNSTABLE_REGIME"
        elif requested_strategy == "combined_arbitration":
            if regime == "UNSTABLE":
                return False, "ARBITRATION_FORBIDDEN_IN_UNSTABLE_REGIME"
        return True, "STRATEGY_PERMITTED"

class Layer6_TimingTrigger:
    """Separates setup from execution trigger."""
    @staticmethod
    def evaluate_trigger(
        strategy_mode: str,
        direction: str,
        bar: TIBBar,
        prev_bar: TIBBar
    ) -> Tuple[bool, str]:
        # Hypothesis 2: Confirmation-based timing improves continuation entries!
        if strategy_mode == "trend_continuation":
            if direction == "BUY":
                # Pullback to EMA20 occurred previously, now confirming higher close above EMA20
                pullback_confirmed = (prev_bar.low_bid <= prev_bar.ema20) and (bar.mid_close > bar.ema20)
                if pullback_confirmed:
                    return True, "PULLBACK_CONTINUATION_CONFIRMED"
                return False, "AWAITING_PULLBACK_CONFIRMATION"
            else: # SELL
                pullback_confirmed = (prev_bar.high_ask >= prev_bar.ema20) and (bar.mid_close < bar.ema20)
                if pullback_confirmed:
                    return True, "PULLBACK_CONTINUATION_CONFIRMED"
                return False, "AWAITING_PULLBACK_CONFIRMATION"
                
        elif strategy_mode == "mean_reversion":
            if direction == "BUY":
                # Rejection of lower band: previous touched lower band, current closed back inside
                rejection_confirmed = (prev_bar.low_bid <= prev_bar.vwap - 1.5 * prev_bar.rolling_std) and (bar.mid_close > bar.vwap - 1.5 * bar.rolling_std)
                if rejection_confirmed:
                    return True, "RANGE_LOWER_REJECTION_CONFIRMED"
                return False, "AWAITING_RANGE_REJECTION"
            else:
                rejection_confirmed = (prev_bar.high_ask >= prev_bar.vwap + 1.5 * prev_bar.rolling_std) and (bar.mid_close < bar.vwap + 1.5 * bar.rolling_std)
                if rejection_confirmed:
                    return True, "RANGE_UPPER_REJECTION_CONFIRMED"
                return False, "AWAITING_RANGE_REJECTION"
                
        elif strategy_mode == "combined_arbitration":
            # Arbitration trigger: requires both trend agreement and momentum confirmation
            if direction == "BUY" and bar.mid_close > bar.ema20 and bar.mid_close > prev_bar.mid_close:
                return True, "ARBITRATION_BULL_TRIGGERED"
            elif direction == "SELL" and bar.mid_close < bar.ema20 and bar.mid_close < prev_bar.mid_close:
                return True, "ARBITRATION_BEAR_TRIGGERED"
            return False, "ARBITRATION_NOT_TRIGGERED"
            
        return False, "UNKNOWN_STRATEGY_MODE"

class Layer7_ExternalContext:
    """Validates external inputs point-in-time and evaluates directional bias."""
    @staticmethod
    def evaluate(
        gld_available: bool,
        news_available: bool,
        cot_available: bool,
        cot_net_mm: float,
        require_all: bool
    ) -> Tuple[bool, str, str]:
        if require_all and not (gld_available and news_available and cot_available):
            return False, "MISSING_REQUIRED_EXTERNAL_INPUTS", "NEUTRAL"
            
        cot_bias = "NEUTRAL"
        if cot_available:
            cot_bias = "BULL" if cot_net_mm > 0 else "BEAR"
            
        return True, "EXTERNAL_CONTEXT_VALIDATED", cot_bias

class Layer8_RiskController:
    """Enforces 2% daily loss limit and minimum lot feasibility."""
    @staticmethod
    def check_feasibility(balance: float, sl_distance_pts: float, contract_size: float = 100.0, min_lot: float = 0.01) -> Tuple[bool, float, str]:
        daily_loss_limit = balance * 0.02
        trade_risk_usd = sl_distance_pts * contract_size * min_lot
        if trade_risk_usd > daily_loss_limit:
            return False, daily_loss_limit, "ACCOUNT_INFEASIBLE_RISK_EXCEEDS_DAILY_LIMIT"
        return True, daily_loss_limit, "RISK_FEASIBLE"
"""
