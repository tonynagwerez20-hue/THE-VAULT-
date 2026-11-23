"""Regression tests aligning the offline reference with MQL broker sizing rules."""

import math

from algomind.account_execution import (
    AccountIdentification,
    Action,
    FeasibilityStatus,
    MinLotStatus,
    SymbolCapabilityProfile,
    evaluate_account_execution,
    validate_symbol_capability,
)
from algomind.risk_controller import RiskController, RiskState


def test_loss_tick_value_drives_risk_when_it_differs_from_profit_value():
    cap = SymbolCapabilityProfile(tick_value=1.0, tick_value_profit=1.0, tick_value_loss=2.0)
    env = evaluate_account_execution(
        AccountIdentification(equity=1000.0, balance=1000.0, margin_free=1000.0),
        cap, 1, 100.0, 99.0, 102.0, target_risk_pct=1.0, max_allowed_distortion=1.0,
    )
    assert env.risk_per_lot == 200.0
    assert env.executable_volume == 0.05
    assert env.actual_risk == 10.0


def test_non_aligned_volume_minimum_uses_first_legal_step_and_rejects_upward_rounding():
    cap = SymbolCapabilityProfile(volume_min=0.01, volume_step=0.03, volume_max=0.10)
    valid, reason = validate_symbol_capability(cap)
    assert (valid, reason) == (True, "OK")

    # Risk budget yields .04 lots, so the legal .03 lot is safe after flooring.
    affordable = evaluate_account_execution(
        AccountIdentification(equity=400.0, balance=400.0, margin_free=400.0),
        cap, 1, 100.0, 99.0, 102.0, target_risk_pct=1.0, max_allowed_distortion=1.0,
    )
    assert affordable.executable_volume == 0.03
    assert affordable.actual_risk <= affordable.target_risk_amount

    # A .02 raw request is below the first legal .03 lot and must not be raised.
    small = evaluate_account_execution(
        AccountIdentification(equity=200.0, balance=200.0, margin_free=200.0),
        cap, 1, 100.0, 99.0, 102.0, target_risk_pct=1.0, max_allowed_distortion=1.0,
    )
    assert small.final_action == Action.NO_TRADE
    assert small.min_lot_status == MinLotStatus.MIN_LOT_UNSAFE
    assert small.actual_risk == 3.0


def test_no_legal_volume_inside_broker_bounds_is_rejected():
    cap = SymbolCapabilityProfile(volume_min=0.04, volume_step=0.03, volume_max=0.05)
    valid, reason = validate_symbol_capability(cap)
    assert (valid, reason) == (False, "INVALID_VOLUME_STEP_GRID")


def test_non_finite_tick_or_volume_metadata_fails_closed():
    for cap in (
        SymbolCapabilityProfile(tick_size=math.nan),
        SymbolCapabilityProfile(tick_value_loss=math.nan, tick_value=math.inf),
        SymbolCapabilityProfile(volume_step=math.inf),
        SymbolCapabilityProfile(volume_max=math.nan),
    ):
        valid, _ = validate_symbol_capability(cap)
        assert not valid

        env = evaluate_account_execution(
            AccountIdentification(equity=1000.0, balance=1000.0, margin_free=1000.0),
            cap, 1, 100.0, 99.0, 102.0,
        )
        assert env.final_action == Action.NO_TRADE
        assert env.feasibility == FeasibilityStatus.INVALID_SYMBOL_SPEC


def test_adaptive_risk_reference_uses_loss_tick_and_legal_minimum_volume():
    result = RiskController(initial_equity=1000.0).evaluate(
        equity=1000.0,
        balance=1000.0,
        stop_distance=1.0,
        tick_size=0.01,
        tick_value=1.0,
        tick_value_loss=2.0,
        volume_min=0.01,
        volume_step=0.03,
    )
    assert result.minimum_lot == 0.03
    assert result.minimum_lot_loss == 6.0
    assert result.trade_allowed


def test_invalid_equity_is_rejected_without_mutating_risk_history():
    controller = RiskController(initial_equity=1000.0)
    before = (controller.initial_equity, controller.high_water_equity, controller.last_equity)
    for equity in (math.nan, math.inf, -math.inf, 0.0, -1.0):
        result = controller.evaluate(equity=equity, balance=1000.0, stop_distance=1.0)
        assert result.risk_state == RiskState.UNSAFE
        assert not result.trade_allowed
        assert (controller.initial_equity, controller.high_water_equity, controller.last_equity) == before
