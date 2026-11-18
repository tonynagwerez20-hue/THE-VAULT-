#!/usr/bin/env python3
"""
AMIGO Python Backtest Engine
Offline prototype replay. Native AMIGO parity is NOT established.
Uses real MT5 tick data, TIB generation, and ported strategy logic.
"""

import math
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import sys
import os
import json

# Add Python directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tib_generator import TIBGenerator
from tib_feature_contract import extract_features

# ============================================================================
# AMIGO CONSTANTS (ported from MQL5 Contracts header.mqh)
# ============================================================================
# Schema version
AMIGO_SCHEMA_VERSION = 1

# Hypothesis / Horizon
HORIZON_SCALPING = 1
HORIZON_INTRADAY = 2
HORIZON_SWING = 3

# Regime
REGIME_TREND_UP = 1
REGIME_TREND_DOWN = 2
REGIME_BALANCED = 3
REGIME_EXPANSION = 4
REGIME_EXHAUSTION = 5
REGIME_NEWS = 6
REGIME_NO_TRADE = 7

# ============================================================================
# RISK CONSTANTS (AMIGO invariants)
# ============================================================================
MAX_RISK_DISTORTION = 5.0
DAILY_HARD_STOP_PCT = 2.0
MIN_REWARD_RISK_RATIO = 2.0
MAX_DAILY_ENTRIES = 5

# ============================================================================
# TICK DATA FETCHING
# ============================================================================
def download_ticks(*args, **kwargs):
    raise RuntimeError("Supply immutable local tick data; implicit terminal access is disabled")

# ============================================================================
# STRATEGY CLASSES (ported from MQL5)
# ============================================================================
class TrendStrategy:
    """Ported from TrendStrategy.mqh - MA cross with RSI confirmation."""

    def __init__(self, ma_period: int = 20, rsi_period: int = 14):
        self.ma_period = ma_period
        self.rsi_period = rsi_period
        self.ma_slow = 0.0
        self.ma_fast = 0.0
        self.rsi = 50.0
        self.trend_up = False
        self.trend_down = False
        self.prices = []

    def update(self, close_price: float):
        """Update indicators with new close price."""
        self.prices.append(close_price)
        if len(self.prices) > self.ma_period:
            self.prices = self.prices[-self.ma_period:]

        if len(self.prices) >= self.ma_period:
            # Slow MA
            self.ma_slow = np.mean(self.prices)
            # Fast MA (half period)
            fast_len = max(1, self.ma_period // 2)
            self.ma_fast = np.mean(self.prices[-fast_len:])

        # RSI calculation
        if len(self.prices) >= 2:
            changes = np.diff(self.prices)
            gains = changes[changes > 0]
            losses = -changes[changes < 0]
            avg_gain = gains.sum() / len(changes)
            avg_loss = losses.sum() / len(changes)
            self.rsi = 50.0 if avg_gain+avg_loss == 0 else 100.0*avg_gain/(avg_gain+avg_loss)

        self.trend_up = self.trend_down = False
        # Trend detection
        if self.ma_fast > self.ma_slow:
            self.trend_up = True
            self.trend_down = False
        elif self.ma_fast < self.ma_slow:
            self.trend_up = False
            self.trend_down = True

    def generate_signal(self) -> Tuple[int, float, str]:
        """Generate trading signal. Returns (direction, confidence, reason)."""
        if len(self.prices) < self.ma_period: return 0, 0.0, "WARMUP"
        if self.trend_up and 50 < self.rsi < 70:
            return 1, self.rsi / 100.0, "MA_CROSS_RSI_BULL"
        elif self.trend_down and 30 < self.rsi < 50:
            return -1, self.rsi / 100.0, "MA_CROSS_RSI_BEAR"
        return 0, 0.0, "NO_SIGNAL"


class MeanReversionStrategy:
    """Ported from MeanReversionStrategy.mqh - RSI reversal."""

    def __init__(self, rsi_period: int = 14, overbought: float = 70.0, oversold: float = 30.0):
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.oversold = oversold
        self.rsi = 50.0
        self.prices = []
        self.bull_div = False
        self.bear_div = False

    def update(self, close_price: float):
        """Update RSI and divergence detection."""
        self.prices.append(close_price)
        if len(self.prices) > self.rsi_period:
            self.prices = self.prices[-self.rsi_period:]

        if len(self.prices) >= 2:
            changes = np.diff(self.prices)
            gains = changes[changes > 0]
            losses = -changes[changes < 0]
            avg_gain = gains.sum() / len(changes)
            avg_loss = losses.sum() / len(changes)
            self.rsi = 50.0 if avg_gain+avg_loss == 0 else 100.0*avg_gain/(avg_gain+avg_loss)

        # Divergence detection (simplified from MQL5)
        if len(self.prices) >= 2:
            price_change = self.prices[-1] - self.prices[-2]
            self.bull_div = (self.rsi < 70) and (self.prices[-1] < self.prices[-2])
            self.bear_div = (self.rsi > 30) and (self.prices[-1] > self.prices[-2])

    def generate_signal(self) -> Tuple[int, float, str]:
        """Generate mean reversion signal."""
        if len(self.prices) < self.rsi_period: return 0, 0.0, "WARMUP"
        if self.bull_div:
            return 1, 1.0 - (self.rsi / 100.0), "RSI_REVERSAL_BULL"
        elif self.bear_div:
            return -1, 1.0 - (self.rsi / 100.0), "RSI_REVERSAL_BEAR"
        return 0, 0.0, "NO_SIGNAL"


# ============================================================================
# POSITION SIZING (AMIGO Risk Invariants)
# ============================================================================
class RiskManager:
    """Implements AMIGO risk invariants for position sizing."""

    def __init__(self, account_balance: float = 10000.0, risk_per_trade_pct: float = 0.5,
                 daily_loss_limit_pct: float = 2.0, max_distortion: float = 5.0,
                 min_rr: float = 2.0):
        if not 0 < risk_per_trade_pct <= 2 or daily_loss_limit_pct != 2 or not 1 <= max_distortion <= 5 or min_rr < 2:
            raise ValueError("Risk policy violation")
        self.day_start = account_balance
        self.balance = account_balance
        self.risk_per_trade = risk_per_trade_pct / 100.0
        self.daily_loss_limit = daily_loss_limit_pct / 100.0
        self.max_distortion = max_distortion
        self.min_rr = min_rr
        self.daily_pnl = 0.0
        self.daily_entries = 0
        self.daily_losses = 0.0

    def reset_daily(self):
        self.day_start = self.balance
        self.daily_pnl = 0.0
        self.daily_entries = 0
        self.daily_losses = 0.0

    def can_trade(self) -> bool:
        if self.daily_entries >= MAX_DAILY_ENTRIES:
            return False
        if self.balance <= self.day_start * (1-self.daily_loss_limit):
            return False
        return True

    def calculate_position_size(self, entry_price: float, stop_price: float,
                                 symbol_info: dict) -> float:
        """Calculate position size per AMIGO risk invariants."""
        keys = ('trade_tick_size','trade_tick_value_loss','volume_min','volume_max','volume_step')
        if any(k not in symbol_info or not math.isfinite(symbol_info[k]) or symbol_info[k]<=0 for k in keys): return 0.0
        if not all(math.isfinite(x) for x in (entry_price,stop_price,self.balance)) or self.balance<=0: return 0.0
        distance=abs(entry_price-stop_price)
        if distance<=0 or not self.can_trade(): return 0.0
        per_lot=distance/symbol_info['trade_tick_size']*symbol_info['trade_tick_value_loss']
        per_lot+=symbol_info.get('commission_per_lot_roundturn',0.)
        per_lot+=symbol_info.get('slippage_price',0.)/symbol_info['trade_tick_size']*symbol_info['trade_tick_value_loss']
        budget=self.balance*self.risk_per_trade
        remaining=max(0.,self.balance-self.day_start*.98)
        cap=min(budget*self.max_distortion,remaining,self.balance*.02)
        step=Decimal(str(symbol_info['volume_step']))
        minimum=(Decimal(str(symbol_info['volume_min']))/step).to_integral_value(rounding=ROUND_CEILING)*step
        raw=min(budget,remaining)/per_lot
        lots=(Decimal(str(min(raw,symbol_info['volume_max'])))/step).to_integral_value(rounding=ROUND_FLOOR)*step
        lots=max(lots,minimum)
        if float(lots)>symbol_info['volume_max'] or float(lots)*per_lot>cap+1e-9: return 0.0
        return float(lots)

    def record_trade(self, pnl: float):
        self.daily_pnl += pnl
        if pnl < 0:
            self.daily_losses += pnl


# ============================================================================
# BACKTEST ENGINE
# ============================================================================
class BacktestEngine:
    def __init__(self, symbol: str = "XAUUSDm", initial_balance: float = 10000.0, symbol_info=None):
        self.symbol = symbol
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.trades = []
        self.equity_curve = []

        # Initialize strategies
        self.trend_strategy = TrendStrategy()
        self.meanrev_strategy = MeanReversionStrategy()
        self.risk_manager = RiskManager(initial_balance)
        self.tib_generator = TIBGenerator(threshold_ticks=100)

        required=('trade_tick_size','trade_tick_value_loss','volume_min','volume_max','volume_step',
                  'commission_per_lot_roundturn','slippage_price','swap_long_per_lot_day','swap_short_per_lot_day','day_offset_seconds')
        if symbol_info is None or any(k not in symbol_info or not math.isfinite(symbol_info[k]) for k in required):
            raise ValueError('Explicit contract, cost, currency and day-boundary specification required')
        if any(symbol_info[k]<0 for k in ('commission_per_lot_roundturn','slippage_price')): raise ValueError('Invalid costs')
        self.symbol_info=dict(symbol_info)
        self.position=None
        self.last_timestamp=None
        self.day=None
        self.pending=None

        # Data
        self.tib_bars = []
        self.current_tib_bar = None

    def run_backtest(self, start_date: datetime, end_date: datetime,
                     tick_count: int = 100000, ticks=None) -> Dict:
        """Run complete backtest."""
        print(f"Starting backtest for {self.symbol} from {start_date} to {end_date}")

        # Download ticks
        if ticks is None: raise ValueError("Immutable local ticks are required")

        for tick in ticks:
            timestamp=int(tick.get('time_msc',tick['time']*1000))
            if start_date.tzinfo is None or end_date.tzinfo is None: raise ValueError('UTC-aware bounds required')
            when=datetime.fromtimestamp(timestamp/1000, tz=start_date.tzinfo)
            if when<start_date or when>=end_date: continue
            bid,ask=float(tick['bid']),float(tick['ask'])
            if not all(math.isfinite(v) for v in (bid,ask)) or bid<=0 or ask<bid or (self.last_timestamp is not None and timestamp<self.last_timestamp):
                raise ValueError('Invalid or unordered quote')
            day=int((timestamp/1000+self.symbol_info['day_offset_seconds'])//86400)
            if day!=self.day:
                if self.position and self.day is not None:
                    key='swap_long_per_lot_day' if self.position['direction']==1 else 'swap_short_per_lot_day'
                    self.balance+=self.position['position_size']*self.symbol_info[key]*(day-self.day)
                self.risk_manager.balance=self.balance
                self.risk_manager.reset_daily()
                if self.position:
                    p=self.position; mark=bid if p['direction']==1 else ask
                    self.risk_manager.day_start+=(mark-p['entry_price'])*p['direction']*p['position_size']*self.symbol_info['trade_tick_value_loss']/self.symbol_info['trade_tick_size']
                self.day=day
            self.last_timestamp=timestamp
            self._mark_position(bid,ask,timestamp)
            self.risk_manager.balance=self.balance
            if self.pending and timestamp>self.pending[3] and self.position is None and self.risk_manager.can_trade():
                direction,confidence,reason,_=self.pending
                price=ask if direction==1 else bid
                self._execute_trade(direction,confidence,reason,price,timestamp)
                self.pending=None
            bar=self.tib_generator.process_tick(dict(bid=bid,ask=ask,time=timestamp/1000,time_msc=timestamp))
            if bar:
                self.trend_strategy.update(bar['close'])
                self.meanrev_strategy.update(bar['close'])
                signal=self._arbitrate(*self.trend_strategy.generate_signal(),*self.meanrev_strategy.generate_signal())
                self.pending=(*signal,timestamp) if signal[0] and self.position is None else None

        # Finalize
        return self._generate_report()

    def _arbitrate(self, trend_dir: int, trend_conf: float, trend_reason: str,
                   mr_dir: int, mr_conf: float, mr_reason: str) -> Tuple[int, float, str]:
        """Arbitration logic from Strategy_Framework.mqh ARB-01 through ARB-07."""
        proposals = []

        if trend_dir != 0:
            proposals.append(('trend', trend_dir, trend_conf, trend_reason))
        if mr_dir != 0:
            proposals.append(('mr', mr_dir, mr_conf, mr_reason))

        if not proposals:
            return 0, 0.0, "NO_SIGNAL"

        # ARB-01: Reject zero direction (already filtered)
        # ARB-02: Data quality veto (not implemented here)
        # ARB-03: Detect duplicates (same direction & entry)
        # ARB-04: Regime compatibility (not implemented)
        # Prototype geometry uses gross RR >=2; native admission remains authoritative.
        # ARB-06/07: Confidence selection

        if len(proposals) == 1:
            return proposals[0][1], proposals[0][2], proposals[0][3]

        return 0, 0.0, "UNCALIBRATED_MULTIPLE_PROPOSALS"

    def _mark_position(self,bid,ask,timestamp):
        equity=self.balance
        if self.position:
            p=self.position; direction=p['direction']; price=bid if direction==1 else ask
            cash_per_price=p['position_size']*self.symbol_info['trade_tick_value_loss']/self.symbol_info['trade_tick_size']
            costs=p['position_size']*self.symbol_info['commission_per_lot_roundturn']
            equity+=(price-p['entry_price'])*direction*cash_per_price-costs
            stopped=(price-p['sl_price'])*direction<=0
            target=(price-p['tp_price'])*direction>=0
            daily=equity<=self.risk_manager.day_start*.98
            if stopped or target or daily:
                fill=(p['tp_price'] if target and not stopped and not daily else price)-direction*self.symbol_info['slippage_price']
                pnl=(fill-p['entry_price'])*direction*cash_per_price-costs
                p.update(exit_price=fill,exit_time=timestamp,pnl=pnl,won=pnl>0,exit_reason='DAILY_STOP' if daily else ('STOP' if stopped else 'TARGET'))
                self.trades.append(p); self.balance+=pnl; self.risk_manager.record_trade(pnl)
                self.position=None; equity=self.balance
        self.equity_curve.append(equity)

    def _execute_trade(self, direction: int, confidence: float, reason: str,
                       entry_price: float, timestamp: int):
        """Execute simulated trade with risk management."""
        if self.position is not None: return
        entry_price+=direction*self.symbol_info['slippage_price']
        # Prototype SL/TP approximation; not native strategy parity
        atr_approx = entry_price * 0.001  # 10 pips for XAUUSD
        stop_distance = atr_approx * 2.0  # 2 ATR stop

        if direction == 1:  # BUY
            sl_price = entry_price - stop_distance
            tp_price = entry_price + stop_distance * 2.0  # 1:2 RR
        else:  # SELL
            sl_price = entry_price + stop_distance
            tp_price = entry_price - stop_distance * 2.0

        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(
            entry_price, sl_price, self.symbol_info
        )

        if position_size <= 0:
            return  # NO_TRADE - min lot infeasible

        # Record trade
        trade = {
            'entry_time': timestamp,
            'entry_price': entry_price,
            'direction': direction,
            'position_size': position_size,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'reason': reason,
            'confidence': confidence,
        }
        self.position=trade
        self.risk_manager.daily_entries+=1

    def _generate_report(self) -> Dict:
        """Generate backtest report."""
        if not self.trades:
            return {
                'error': 'No trades executed',
                'balance': self.balance,
                'initial_balance': self.initial_balance,
            }

        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.get('won', False))
        losing_trades = total_trades - winning_trades

        gross_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] < 0))

        net_profit = self.balance - self.initial_balance
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        win_rate = winning_trades / total_trades
        expectancy = net_profit / total_trades

        # Drawdown
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        max_drawdown = np.max(drawdown) * 100

        return {
            'symbol': self.symbol,
            'scope': 'Offline prototype only; native AMIGO parity not established',
            'open_position': self.position,
            'specification': self.symbol_info,
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'net_profit': net_profit,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'max_drawdown_pct': max_drawdown,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'avg_win': gross_profit / winning_trades if winning_trades > 0 else 0,
            'avg_loss': gross_loss / losing_trades if losing_trades > 0 else 0,
            'max_daily_entries': MAX_DAILY_ENTRIES,
        }


def main():
    raise SystemExit("Use BacktestEngine with immutable local bid/ask ticks and explicit broker/cost specifications; native MT5 remains authoritative.")

if __name__ == "__main__": main()
