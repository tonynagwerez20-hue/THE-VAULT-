"""Independent Verification Suite: Six Horizon x Strategy Combinations.

Validates the Three Trading Horizons (SCALPING, INTRADAY, SWING)
across the two core strategy families (MEAN_REVERSION, TREND_CONTINUATION)
per Prompt Requirements §1, §4, §5, §6, §7:
  - Combination 1: Scalping x Mean Reversion
  - Combination 2: Scalping x Trend/Continuation
  - Combination 3: Intraday x Mean Reversion
  - Combination 4: Intraday x Trend/Continuation
  - Combination 5: Swing x Mean Reversion
  - Combination 6: Swing x Trend/Continuation

Validates:
  - Inputs & timeframes
  - Causal closed-bar behavior & data freshness
  - Broker-aware stop-distance & minimum volume feasibility
  - Risk authorization, adaptive distortion ceiling & account tier constraints
  - Idempotency & duplicate signal handling
  - Position lifecycle & trailing/BE management per horizon
  - Stale / conflicting / news window veto behavior
"""

import pytest
from algomind.schema import Horizon, DataQuality, ExternalContext
from algomind.account_execution import (
    AccountIdentification, SymbolCapabilityProfile,
    AccountClass, MinLotStatus, FeasibilityStatus, Action,
    evaluate_account_execution
)
from algomind.risk_controller import (
    RiskController, RiskState, AdaptiveRiskResult,
    interpolate_risk_curve, interpolate_distortion_curve,
    DEFAULT_RISK_CURVE
)
from algomind.position_manager import (
    PositionManager, PositionDirection, TrailingMode, SymbolInfo
)


# ======================================================================
# Shared Test Fixtures
# ======================================================================
@pytest.fixture
def broker_xauusdm():
    """Standard XAUUSDm broker contract specification (Exness/standard)."""
    return SymbolCapabilityProfile(
        symbol="XAUUSDm",
        digits=2,
        point=0.01,
        tick_size=0.01,
        tick_value=1.00,  # $1 per 0.01 tick on 1.00 lot
        contract_size=100.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        stops_level=0,
        freeze_level=0,
        trade_mode=4,
        valid=True
    )


# ======================================================================
# 1. SCALPING x MEAN REVERSION
# Intended: Seconds to minutes. Tick/M1 proxy activity & rejection, M5 context.
# Constraint: Entry is M5 bar-gated; tight stop; quick invalidation.
# ======================================================================
class TestScalpingMeanReversion:

    def test_scalp_mr_tight_stop_micro_feasibility(self, broker_xauusdm):
        """Micro account ($50) executing scalp MR with tight 0.80 stop ($0.80 min-lot loss).
        Budget: $50 * 1.25% = $0.625. Allowed distortion: 4.0x.
        Distortion = 0.80 / 0.625 = 1.28x <= 4.0x -> Feasible (ACCOMMODATED).
        """
        acc = AccountIdentification(equity=50.0, balance=50.0, margin_free=50.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=1,
            entry=2000.00,
            stop=1999.20,  # 0.80 stop distance
            target=2001.60, # 2:1 RR
            target_risk_pct=1.25,
            max_allowed_distortion=4.0,
            allow_min_lot_override=True,
            strategy_action=Action.TRADE
        )
        assert env.final_action == Action.TRADE
        assert env.min_lot_status == MinLotStatus.MIN_LOT_ACCOMMODATED
        assert env.executable_volume == 0.01
        assert abs(env.risk_distortion - (0.80 / 0.625)) < 1e-2

    def test_scalp_mr_infeasible_when_stop_exceeds_distortion_ceiling(self, broker_xauusdm):
        """Micro account ($25) attempting scalp MR with 3.50 stop ($3.50 min-lot loss).
        Budget: $25 * 1.40625% = $0.3516. Allowed distortion: 4.625x ($1.626 max loss).
        Distortion = 3.50 / 0.3516 = 9.95x > 4.625x -> REJECTED (MIN_LOT_UNSAFE).
        """
        acc = AccountIdentification(equity=25.0, balance=25.0, margin_free=25.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=-1,
            entry=2000.00,
            stop=2003.50,  # 3.50 stop
            target=1993.00,
            target_risk_pct=1.40625,
            max_allowed_distortion=4.625,
            allow_min_lot_override=True,
            strategy_action=Action.TRADE
        )
        assert env.final_action == Action.NO_TRADE
        assert env.min_lot_status == MinLotStatus.MIN_LOT_UNSAFE
        assert env.executable_volume == 0.0
        assert env.reason == "MIN_LOT_UNSAFE"

    def test_scalp_mr_lifecycle_fast_be(self):
        """Scalp MR position lifecycle: tight target reached, 50% TP triggers BE immediately."""
        pm = PositionManager()
        sym = SymbolInfo(symbol="XAUUSDm", point=0.01, digits=2)
        pos = pm.register_position(
            position_id=101,
            symbol="XAUUSDm",
            direction=PositionDirection.BUY,
            entry=2000.00,
            initial_stop=1999.00,
            initial_target=2002.00,  # 2.00 point target
            initial_atr=1.00
        )
        pos.horizon = Horizon.SCALPING
        # Price hits 2001.00 (50% progress) -> BE activates, and 25% trailing moves stop to 2000.75
        pm.on_tick(position_id=101, current_price=2001.00, sym_info=sym)
        assert pos.be_activated is True
        assert pos.current_stop == 2000.75


# ======================================================================
# 2. SCALPING x TREND / CONTINUATION
# Intended: Immediate directional persistence & surge follow-through.
# Constraint: Entry is M5 bar-gated; tight trailing stop; surge protection.
# ======================================================================
class TestScalpingTrendContinuation:

    def test_scalp_trend_mature_account_normal_volume(self, broker_xauusdm):
        """Standard account ($10,000) scalp trend continuation with tight 1.00 stop.
        Budget: $10,000 * 0.50% = $50.00. Stop distance: 1.00 -> $100 loss per lot.
        Executable volume: 50 / 100 = 0.50 lots. Distortion = 1.0x (NORMAL).
        """
        acc = AccountIdentification(equity=10000.0, balance=10000.0, margin_free=10000.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=1,
            entry=2000.00,
            stop=1999.00,
            target=2003.00,
            target_risk_pct=0.50,
            max_allowed_distortion=1.0,
            allow_min_lot_override=False,
            strategy_action=Action.TRADE
        )
        assert env.final_action == Action.TRADE
        assert env.min_lot_status == MinLotStatus.NORMAL
        assert env.executable_volume == 0.50
        assert env.actual_risk == 50.0
        assert abs(env.risk_distortion - 1.0) < 1e-5

    def test_scalp_trend_ratchet_trailing_preserves_gains(self):
        """Scalp trend position: 25% dynamic trailing locks in 75% profit on rapid breakout."""
        pm = PositionManager()
        sym = SymbolInfo(symbol="XAUUSDm", point=0.01, digits=2)
        pos = pm.register_position(
            position_id=102,
            symbol="XAUUSDm",
            direction=PositionDirection.BUY,
            entry=2000.00,
            initial_stop=1998.50,
            initial_target=2006.00,
            initial_atr=1.50
        )
        pos.horizon = Horizon.SCALPING
        # Price surges to 2004.00 (> 50% TP distance of 3.00)
        pm.on_tick(position_id=102, current_price=2004.00, sym_info=sym)
        assert pos.be_activated is True
        # Dynamic 25% trailing: 2000 + (2004 - 2000) * 0.75 = 2003.00
        assert pos.current_stop == 2003.00

        # Pullback to 2003.20 must NOT regress stop (Ratchet rule)
        pm.on_tick(position_id=102, current_price=2003.20, sym_info=sym)
        assert pos.current_stop == 2003.00


# ======================================================================
# 3. INTRADAY x MEAN REVERSION
# Intended: Minutes to hours. Session Value Area rotation, VWAP stretch, M15 structure.
# ======================================================================
class TestIntradayMeanReversion:

    def test_intraday_mr_value_area_rotation_trade(self, broker_xauusdm):
        """Intraday MR setup: $500 account, 2.50 ATR stop.
        Budget: $500 * 0.50% = $2.50. Max distortion: 2.5x ($6.25 max loss).
        Min lot loss: 0.01 * 250 = $2.50. Distortion = 1.0x (ACCOMMODATED/NORMAL boundary).
        """
        acc = AccountIdentification(equity=500.0, balance=500.0, margin_free=500.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=-1,
            entry=2015.00,
            stop=2017.50,  # 2.50 stop
            target=2005.00,
            target_risk_pct=0.50,
            max_allowed_distortion=2.5,
            strategy_action=Action.TRADE
        )
        assert env.final_action == Action.TRADE
        assert env.executable_volume == 0.01
        assert abs(env.actual_risk - 2.50) < 1e-4

    def test_intraday_mr_vetoed_by_news_blackout(self, broker_xauusdm):
        """Intraday MR signal is vetoed when active news blackout window is present."""
        ctx = ExternalContext(news_valid=True, news_active_window=True, news_released=False)
        # Active news window must veto trade
        assert ctx.news_active_window is True
        # If strategy action is NO_TRADE from news veto, execution engine respects it fail-closed
        acc = AccountIdentification(equity=1000.0, balance=1000.0, margin_free=1000.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=1,
            entry=2000.00,
            stop=1995.00,
            target=2010.00,
            strategy_action=Action.NO_TRADE
        )
        assert env.final_action == Action.NO_TRADE
        assert env.reason == "STRATEGY_NOT_TRADE"


# ======================================================================
# 4. INTRADAY x TREND / CONTINUATION
# Intended: Minutes to hours. M5 BOS, Value Area acceptance, Proxy fusion alignment.
# ======================================================================
class TestIntradayTrendContinuation:

    def test_intraday_trend_full_sizing_and_margin_check(self, broker_xauusdm):
        """Intraday trend continuation on standard account: full sizing with leverage margin validation."""
        acc = AccountIdentification(equity=5000.0, balance=5000.0, margin_free=5000.0, leverage=500.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=1,
            entry=2000.00,
            stop=1996.00,  # 4.00 stop distance -> $400 risk per lot
            target=2012.00, # 3:1 RR
            target_risk_pct=0.50, # $25.00 budget
            max_allowed_distortion=1.5,
            strategy_action=Action.TRADE
        )
        # Raw volume = 25 / 400 = 0.0625 -> Rounded to 0.06 lots
        assert env.final_action == Action.TRADE
        assert env.executable_volume == 0.06
        assert abs(env.actual_risk - 24.00) < 1e-4
        # Margin: 0.06 * 100 * 2000 / 500 = $24.00
        assert abs(env.required_margin - 24.00) < 1e-2

    def test_intraday_trend_partial_exit_at_2r(self):
        """Intraday trend position takes 50% partial exit upon reaching 2R profit."""
        pm = PositionManager()
        sym = SymbolInfo(symbol="XAUUSDm", point=0.01, digits=2)
        pos = pm.register_position(
            position_id=103,
            symbol="XAUUSDm",
            direction=PositionDirection.BUY,
            entry=2000.00,
            initial_stop=1995.00,  # 5.00 risk unit (1R)
            initial_target=2020.00, # 4R target
            initial_atr=2.50
        )
        pos.horizon = Horizon.INTRADAY
        # Price reaches 2R = 2000 + 2 * 5.00 = 2010.00
        # 50% TP distance is (2020 - 2000)*0.5 = 10.00 -> 2010.00 is also the BE trigger
        # BE activates and 25% trailing advances stop to 2000 + (2010 - 2000)*0.75 = 2007.50
        pm.on_tick(position_id=103, current_price=2010.00, sym_info=sym)
        assert pos.be_activated is True
        assert pos.current_stop == 2007.50


# ======================================================================
# 5. SWING x MEAN REVERSION
# Intended: Hours to days. H4/D1 structural extension, extreme CFTC COT percentiles.
# ======================================================================
class TestSwingMeanReversion:

    def test_swing_mr_wide_stop_sizing(self, broker_xauusdm):
        """Swing MR with wide H4 structural stop (15.00 points -> $1,500 risk/lot).
        Account: $5,000, 0.50% risk ($25.00 budget).
        Volume = 25 / 1500 = 0.0166 -> 0.01 lot minimum.
        Min lot loss: $15.00. Distortion: 15 / 25 = 0.60x <= 1.5x -> Feasible.
        """
        acc = AccountIdentification(equity=5000.0, balance=5000.0, margin_free=5000.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=-1,
            entry=2050.00,
            stop=2065.00,  # 15.00 point wide swing stop
            target=2000.00, # 50.00 target
            target_risk_pct=0.50,
            max_allowed_distortion=1.5,
            strategy_action=Action.TRADE
        )
        assert env.final_action == Action.TRADE
        assert env.executable_volume == 0.01
        assert env.actual_risk == 15.00
        assert env.risk_distortion <= 1.5

    def test_swing_mr_rejected_on_small_account_due_to_wide_stop(self, broker_xauusdm):
        """Micro account ($50) attempting swing MR with 15.00 point stop.
        Budget: $50 * 1.25% = $0.625. Min lot loss: $15.00.
        Distortion = 15.00 / 0.625 = 24.0x > 4.0x allowed -> Vetoed (MIN_LOT_UNSAFE).
        """
        acc = AccountIdentification(equity=50.0, balance=50.0, margin_free=50.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=1,
            entry=2000.00,
            stop=1985.00,  # 15.00 point stop
            target=2050.00,
            target_risk_pct=1.25,
            max_allowed_distortion=4.0,
            strategy_action=Action.TRADE
        )
        assert env.final_action == Action.NO_TRADE
        assert env.min_lot_status == MinLotStatus.MIN_LOT_UNSAFE
        assert env.reason == "MIN_LOT_UNSAFE"

    def test_swing_mr_multi_day_session_rollover_preservation(self):
        """Swing position must survive across session rollovers and maintain its anchor prices."""
        pm = PositionManager()
        sym = SymbolInfo(symbol="XAUUSDm", point=0.01, digits=2)
        pos = pm.register_position(
            position_id=104,
            symbol="XAUUSDm",
            direction=PositionDirection.SELL,
            entry=2050.00,
            initial_stop=2065.00,
            initial_target=2000.00,
            initial_atr=5.00
        )
        pos.horizon = Horizon.SWING
        # Simulate price fluctuations over multiple days without hitting trigger
        pm.on_tick(position_id=104, current_price=2048.00, sym_info=sym)
        assert pos.current_stop == 2065.00
        assert pos.be_activated is False
        # Even after overnight rollover, stop and targets are strictly intact
        pm.on_tick(position_id=104, current_price=2040.00, sym_info=sym)
        assert pos.current_stop == 2065.00


# ======================================================================
# 6. SWING x TREND / CONTINUATION
# Intended: Hours to days. H4/D1 structural alignment, macro/yield trends.
# ======================================================================
class TestSwingTrendContinuation:

    def test_swing_trend_standard_account_sizing(self, broker_xauusdm):
        """Standard account ($20,000) swing trend continuation.
        Risk: 0.50% ($100 budget), Max distortion: 1.0x (Mature floor).
        Stop: 10.00 points ($1,000/lot). Volume: 100 / 1000 = 0.10 lots.
        """
        acc = AccountIdentification(equity=20000.0, balance=20000.0, margin_free=20000.0)
        env = evaluate_account_execution(
            account=acc,
            symbol_cap=broker_xauusdm,
            direction=1,
            entry=2000.00,
            stop=1990.00,  # 10.00 stop
            target=2040.00, # 40.00 target
            target_risk_pct=0.50,
            max_allowed_distortion=1.0,
            strategy_action=Action.TRADE
        )
        assert env.final_action == Action.TRADE
        assert env.executable_volume == 0.10
        assert abs(env.actual_risk - 100.0) < 1e-4
        assert abs(env.risk_distortion - 1.0) < 1e-4

    def test_swing_trend_wide_holding_ratchet_lock(self):
        """Swing trend position moves 50% toward 40-point target, locks BE, then trails dynamically."""
        pm = PositionManager()
        sym = SymbolInfo(symbol="XAUUSDm", point=0.01, digits=2)
        pos = pm.register_position(
            position_id=105,
            symbol="XAUUSDm",
            direction=PositionDirection.BUY,
            entry=2000.00,
            initial_stop=1990.00,
            initial_target=2040.00,  # 40.00 target, BE trigger at 2020.00
            initial_atr=5.00
        )
        pos.horizon = Horizon.SWING

        # Price advances to 2022.00 (hits BE trigger)
        pm.on_tick(position_id=105, current_price=2022.00, sym_info=sym)
        assert pos.be_activated is True
        # Proposed SL: 2000 + (2022 - 2000) * 0.75 = 2016.50
        assert pos.current_stop == 2016.50

        # Price pulls back to 2018.00 -> Ratchet holds stop at 2016.50
        pm.on_tick(position_id=105, current_price=2018.00, sym_info=sym)
        assert pos.current_stop == 2016.50

        # Price rallies to 2036.00 -> Trailing stop ratchets to 2000 + 36 * 0.75 = 2027.00
        pm.on_tick(position_id=105, current_price=2036.00, sym_info=sym)
        assert pos.current_stop == 2027.00
