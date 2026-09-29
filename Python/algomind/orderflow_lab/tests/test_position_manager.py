"""Comprehensive Unit Tests & State-Transition Tests for Position Manager.

Covers prompt Sections 13 and 14:
  - BUY & SELL mathematical formulas for 25% dynamic trailing
  - BE trigger at 50% of Entry->TP distance
  - Ratcheting rules (BUY & SELL)
  - Price retracements & SL hold behavior
  - Broker stop distance constraints & symbol precision
  - Complete state-transition lifecycle sequences for BUY and SELL positions
"""

import pytest
from algomind.position_manager import (
    PositionManager, PositionDirection, TrailingMode, SymbolInfo,
    calculate_25pct_trailing_sl, calculate_be_trigger_price
)


# ======================================================================
# Section 13: Mathematical Formula Unit Tests
# ======================================================================
class TestMathematicalFormulas:

    def test_buy_trailing_sl_calculations(self):
        # Entry = 100, Current = 110 -> Expected: 107.5
        sl_110 = calculate_25pct_trailing_sl(entry=100.0, current_price=110.0, direction=PositionDirection.BUY)
        assert abs(sl_110 - 107.5) < 1e-6

        # Entry = 100, Current = 120 -> Expected: 115.0
        sl_120 = calculate_25pct_trailing_sl(entry=100.0, current_price=120.0, direction=PositionDirection.BUY)
        assert abs(sl_120 - 115.0) < 1e-6

        # Entry = 100, Current = 130 -> Expected: 122.5
        sl_130 = calculate_25pct_trailing_sl(entry=100.0, current_price=130.0, direction=PositionDirection.BUY)
        assert abs(sl_130 - 122.5) < 1e-6

    def test_sell_trailing_sl_calculations(self):
        # Entry = 100, Current = 90 -> Expected: 92.5
        sl_90 = calculate_25pct_trailing_sl(entry=100.0, current_price=90.0, direction=PositionDirection.SELL)
        assert abs(sl_90 - 92.5) < 1e-6

        # Entry = 100, Current = 80 -> Expected: 85.0
        sl_80 = calculate_25pct_trailing_sl(entry=100.0, current_price=80.0, direction=PositionDirection.SELL)
        assert abs(sl_80 - 85.0) < 1e-6

        # Entry = 100, Current = 70 -> Expected: 77.5
        sl_70 = calculate_25pct_trailing_sl(entry=100.0, current_price=70.0, direction=PositionDirection.SELL)
        assert abs(sl_70 - 77.5) < 1e-6

    def test_be_trigger_price(self):
        # BUY: Entry = 100, Target = 140 -> TPDistance = 40, 50% = 20 -> BETrigger = 120
        be_buy = calculate_be_trigger_price(entry=100.0, target=140.0, direction=PositionDirection.BUY)
        assert abs(be_buy - 120.0) < 1e-6

        # SELL: Entry = 100, Target = 60 -> TPDistance = 40, 50% = 20 -> BETrigger = 80
        be_sell = calculate_be_trigger_price(entry=100.0, target=60.0, direction=PositionDirection.SELL)
        assert abs(be_sell - 80.0) < 1e-6


# ======================================================================
# Section 13: Position Manager Edge Cases & Guards
# ======================================================================
class TestPositionManagerEdgeCases:

    def test_be_not_yet_reached(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)
        # BUY: Entry = 100, Initial SL = 90, Initial TP = 140 -> BE Trigger = 120
        pos = pm.register_position(1, "XAUUSD", PositionDirection.BUY, 100.0, 90.0, 140.0, 2.0)

        # Price = 110 (50% progress not reached yet)
        pos_out, logs = pm.on_tick(1, 110.0, sym)
        assert pos_out.be_activated is False
        assert pos_out.current_stop == 90.0
        assert any("[BE_CHECK]" in l and "PENDING" in l for l in logs)

    def test_be_reached_and_activated(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)
        pos = pm.register_position(1, "XAUUSD", PositionDirection.BUY, 100.0, 90.0, 140.0, 2.0)

        # Price = 120 (Exactly 50% progress to TP)
        pos_out, logs = pm.on_tick(1, 120.0, sym)
        assert pos_out.be_activated is True
        # Trailing at 120: profit=20, 25% trail = 115 > 100 (BE) > 90
        assert pos_out.current_stop == 115.0
        assert any("[BE_ACTIVATED]" in l for l in logs)

    def test_buy_ratchet_holding(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)
        pm.register_position(1, "XAUUSD", PositionDirection.BUY, 100.0, 90.0, 140.0, 2.0)

        # Move price to 120 -> SL set to 115
        pm.on_tick(1, 120.0, sym)
        assert pm.positions[1].current_stop == 115.0

        # Price retraces to 116 -> proposed trailing SL = 116 - 4 = 112
        # Since 112 < 115 (worse than existing), SL MUST NOT LOOSEN
        pos_out, logs = pm.on_tick(1, 116.0, sym)
        assert pos_out.current_stop == 115.0
        assert any("[TRAIL_HOLD]" in l and "NO_IMPROVEMENT" in l for l in logs)

    def test_sell_ratchet_holding(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)
        # SELL: Entry = 100, Initial SL = 110, Initial TP = 60 -> BE Trigger = 80
        pm.register_position(2, "XAUUSD", PositionDirection.SELL, 100.0, 110.0, 60.0, 2.0)

        # Move price down to 80 -> profit=20, 25% trail = 85
        pm.on_tick(2, 80.0, sym)
        assert pm.positions[2].current_stop == 85.0

        # Price retraces up to 84 -> proposed trailing SL = 84 + 4 = 88
        # Since 88 > 85 (worse for short), SL MUST NOT LOOSEN
        pos_out, logs = pm.on_tick(2, 84.0, sym)
        assert pos_out.current_stop == 85.0
        assert any("[TRAIL_HOLD]" in l and "NO_IMPROVEMENT" in l for l in logs)

    def test_tp_reached(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)
        pm.register_position(1, "XAUUSD", PositionDirection.BUY, 100.0, 90.0, 140.0, 2.0)

        pos_out, logs = pm.on_tick(1, 140.5, sym)
        assert pos_out.is_closed is True
        assert pos_out.close_reason == "TAKE_PROFIT"
        assert any("[POSITION_EXIT]" in l and "reason=TAKE_PROFIT" in l for l in logs)

    def test_invalid_zero_distance_tp(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)
        # Zero/missing TP
        pm.register_position(1, "XAUUSD", PositionDirection.BUY, 100.0, 90.0, 0.0, 2.0)

        pos_out, logs = pm.on_tick(1, 105.0, sym)
        assert any("[TRAIL_BLOCKED]" in l and "reason=INVALID_TP" in l for l in logs)

    def test_missing_position(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)

        pos_out, logs = pm.on_tick(999, 105.0, sym)
        assert pos_out is None
        assert any("[TRAIL_BLOCKED]" in l and "reason=MISSING_POSITION" in l for l in logs)

    def test_broker_stops_level_restriction(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        # stops_level = 500 points = 5.00 distance
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01, stops_level=500)
        pm.register_position(1, "XAUUSD", PositionDirection.BUY, 100.0, 90.0, 140.0, 2.0)

        # Price = 120 -> proposed SL = 115. Dist = 120 - 115 = 5.00 >= 5.00 -> OK!
        pos_out, logs = pm.on_tick(1, 120.0, sym)
        assert pos_out.current_stop == 115.0

        # Now test with strict stops level = 600 points (6.00 distance)
        sym_strict = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01, stops_level=600)
        # Reset position
        pm2 = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        pm2.register_position(1, "XAUUSD", PositionDirection.BUY, 100.0, 90.0, 140.0, 2.0)
        pos_out2, logs2 = pm2.on_tick(1, 120.0, sym_strict)
        assert any("[TRAIL_BLOCKED]" in l and "STOPS_LEVEL" in l for l in logs2)

    def test_symbol_precision_normalization(self):
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        # 3 decimal places
        sym = SymbolInfo(symbol="XAUUSD", digits=3, point=0.001)
        pm.register_position(1, "XAUUSD", PositionDirection.BUY, 100.123, 90.000, 140.000, 2.0)

        # Price = 120.456 -> profit = 20.333 -> 25% trail = 5.08325 -> proposed SL = 115.37275 -> rounded to 3 digits: 115.373
        pos_out, logs = pm.on_tick(1, 120.456, sym)
        assert pos_out.current_stop == 115.373


# ======================================================================
# Section 14: Complete State-Transition Sequence Tests
# ======================================================================
class TestStateTransitionSequence:

    def test_complete_buy_sequence(self):
        """Verify complete BUY sequence from open to trailing to exit."""
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)

        # 1. Position opened
        pos = pm.register_position(
            position_id=101,
            symbol="XAUUSD",
            direction=PositionDirection.BUY,
            entry=100.0,
            initial_stop=90.0,
            initial_target=140.0,
            initial_atr=2.0
        )
        assert pos.current_stop == 90.0
        assert pos.be_activated is False

        # 2. Price below 50% TP progress (BE trigger = 120.0)
        pos, logs = pm.on_tick(101, 110.0, sym)
        assert pos.be_activated is False
        assert pos.current_stop == 90.0

        # 3. Price reaches 50% progress (Current = 120.0) -> BE activates & trailing starts
        # Profit = 20 -> 25% trail SL = 115.0
        pos, logs = pm.on_tick(101, 120.0, sym)
        assert pos.be_activated is True
        assert pos.current_stop == 115.0

        # 4. Price continues favorably (Current = 130.0)
        # Profit = 30 -> 25% trail SL = 122.5
        pos, logs = pm.on_tick(101, 130.0, sym)
        assert pos.current_stop == 122.5

        # 5. Price ratchets again (Current = 136.0)
        # Profit = 36 -> 25% trail SL = 127.0
        pos, logs = pm.on_tick(101, 136.0, sym)
        assert pos.current_stop == 127.0

        # 6. Price retraces (Current = 130.0) -> SL does NOT loosen!
        pos, logs = pm.on_tick(101, 130.0, sym)
        assert pos.current_stop == 127.0
        assert any("[TRAIL_HOLD]" in l for l in logs)

        # 7. Price drops to hit SL (Current = 126.5) -> Position exits!
        pos, logs = pm.on_tick(101, 126.5, sym)
        assert pos.is_closed is True
        assert pos.close_reason == "STOP_LOSS"
        assert any("[POSITION_EXIT]" in l and "STOP_LOSS" in l for l in logs)

    def test_complete_sell_sequence(self):
        """Verify complete SELL sequence from open to trailing to exit."""
        pm = PositionManager(trailing_mode=TrailingMode.DYNAMIC_25_PERCENT)
        sym = SymbolInfo(symbol="XAUUSD", digits=2, point=0.01)

        # 1. Position opened
        pos = pm.register_position(
            position_id=202,
            symbol="XAUUSD",
            direction=PositionDirection.SELL,
            entry=100.0,
            initial_stop=110.0,
            initial_target=60.0,
            initial_atr=2.0
        )
        assert pos.current_stop == 110.0
        assert pos.be_activated is False

        # 2. Price above 50% TP progress (BE trigger = 80.0)
        pos, logs = pm.on_tick(202, 90.0, sym)
        assert pos.be_activated is False
        assert pos.current_stop == 110.0

        # 3. Price reaches 50% progress (Current = 80.0) -> BE activates & trailing starts
        # Profit = 20 -> 25% trail SL = 85.0
        pos, logs = pm.on_tick(202, 80.0, sym)
        assert pos.be_activated is True
        assert pos.current_stop == 85.0

        # 4. Price continues favorably (Current = 70.0)
        # Profit = 30 -> 25% trail SL = 77.5
        pos, logs = pm.on_tick(202, 70.0, sym)
        assert pos.current_stop == 77.5

        # 5. Price ratchets again (Current = 64.0)
        # Profit = 36 -> 25% trail SL = 73.0
        pos, logs = pm.on_tick(202, 64.0, sym)
        assert pos.current_stop == 73.0

        # 6. Price retraces up (Current = 70.0) -> SL does NOT loosen!
        pos, logs = pm.on_tick(202, 70.0, sym)
        assert pos.current_stop == 73.0
        assert any("[TRAIL_HOLD]" in l for l in logs)

        # 7. Price rises to hit SL (Current = 73.5) -> Position exits!
        pos, logs = pm.on_tick(202, 73.5, sym)
        assert pos.is_closed is True
        assert pos.close_reason == "STOP_LOSS"
        assert any("[POSITION_EXIT]" in l and "STOP_LOSS" in l for l in logs)
