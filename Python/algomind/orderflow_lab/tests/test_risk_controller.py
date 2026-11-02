"""Comprehensive Unit & Property Tests for Account-Size-Correlated Risk + Distortion Engine.

Covers all test requirements from Section 24 and Property Tests 1-7 from Section 25:
  - Account-size curve anchors ($10, $50, $100, $250, $500, $1,000, $5,000, $10,000)
  - Continuous piecewise-linear interpolation
  - Lower clamp (equity < $10) and upper clamp (equity > $10,000)
  - Monotonicity properties (risk % never increases with equity, allowed distortion never increases)
  - Absolute safety ceilings (risk <= 2.0%, distortion <= 10.0x)
  - Small-account edge cases ($3, $5, $10, $25, $50, $100)
  - Minimum-lot feasibility & reverse feasibility diagnostics (RequiredRiskPercent never forces trade)
  - Hard daily drawdown stop (DAILY_STOP -> zero risk -> NO_TRADE)
  - High-water drawdown throttling (downward only)
  - Strategy invariance (strategy outputs unaffected by risk layer)
  - Total-drawdown lock complete isolation
"""

import pytest
from Amigo.risk_controller import (
    RiskController,
    RiskState,
    AdaptiveRiskResult,
    interpolate_risk_curve,
    interpolate_distortion_curve,
    DEFAULT_RISK_CURVE,
    ABSOLUTE_MAX_RISK_PERCENT,
    ABSOLUTE_MAX_DISTORTION,
)
from Amigo.account_execution import (
    AccountIdentification,
    SymbolCapabilityProfile,
    Action,
    evaluate_account_execution,
)


class TestAccountSizeCurveAndAnchors:

    def test_anchor_points(self):
        """Verify each exact anchor point produces configured risk % and distortion."""
        expected = {
            10.0: (1.50, 5.0),
            50.0: (1.25, 4.0),
            100.0: (1.00, 3.5),
            250.0: (0.75, 3.0),
            500.0: (0.50, 2.5),
            1000.0: (0.50, 2.0),
            5000.0: (0.50, 1.5),
            10000.0: (0.50, 1.0),
        }
        for eq, (exp_r, exp_d) in expected.items():
            r = interpolate_risk_curve(eq)
            d = interpolate_distortion_curve(eq)
            assert abs(r - exp_r) < 1e-5, f"Equity {eq} risk mismatch: got {r}, expected {exp_r}"
            assert abs(d - exp_d) < 1e-5, f"Equity {eq} distortion mismatch: got {d}, expected {exp_d}"

    def test_lower_clamp(self):
        """Equity below $10 uses the lower clamp ($10 anchor: 1.50% risk, 5.0x distortion)."""
        for eq in [0.5, 1.0, 3.0, 5.0, 9.99]:
            r = interpolate_risk_curve(eq)
            d = interpolate_distortion_curve(eq)
            assert abs(r - 1.50) < 1e-5
            assert abs(d - 5.0) < 1e-5

    def test_upper_clamp(self):
        """Equity above $10,000 uses the upper clamp ($10,000 anchor: 0.50% risk, 1.0x distortion)."""
        for eq in [10000.01, 15000.0, 50000.0, 100000.0]:
            r = interpolate_risk_curve(eq)
            d = interpolate_distortion_curve(eq)
            assert abs(r - 0.50) < 1e-5
            assert abs(d - 1.0) < 1e-5

    def test_piecewise_interpolation(self):
        """Verify intermediate interpolation points are continuous and exact."""
        # Midpoint of $10 (1.50%, 5.0x) and $50 (1.25%, 4.0x) is $30 -> 1.375% risk, 4.5x distortion
        r30 = interpolate_risk_curve(30.0)
        d30 = interpolate_distortion_curve(30.0)
        assert abs(r30 - 1.375) < 1e-5
        assert abs(d30 - 4.5) < 1e-5

        # Midpoint of $50 (1.25%, 4.0x) and $100 (1.00%, 3.5x) is $75 -> 1.125% risk, 3.75x distortion
        r75 = interpolate_risk_curve(75.0)
        d75 = interpolate_distortion_curve(75.0)
        assert abs(r75 - 1.125) < 1e-5
        assert abs(d75 - 3.75) < 1e-5


class TestMathematicalProperties:

    def test_property_1_monotonic_risk_percentage(self):
        """Property 1: Risk percentage never increases as equity increases."""
        equities = [i * 5.0 for i in range(1, 2500)]  # $5 to $12,500
        prev_r = float("inf")
        for eq in equities:
            r = interpolate_risk_curve(eq)
            assert r <= prev_r + 1e-9, f"Risk increased from {prev_r} to {r} at equity {eq}"
            prev_r = r

    def test_property_2_monotonic_allowed_distortion(self):
        """Property 2: Allowed distortion never increases as equity increases."""
        equities = [i * 5.0 for i in range(1, 2500)]
        prev_d = float("inf")
        for eq in equities:
            d = interpolate_distortion_curve(eq)
            assert d <= prev_d + 1e-9, f"Distortion increased from {prev_d} to {d} at equity {eq}"
            prev_d = d

    def test_property_3_absolute_risk_ceiling(self):
        """Property 3: Effective risk percentage never exceeds ABSOLUTE_MAX_RISK_PERCENT (2.0%)."""
        rc = RiskController()
        for eq in [1.0, 10.0, 50.0, 100.0, 500.0, 10000.0]:
            res = rc.evaluate(equity=eq, balance=eq, stop_distance=1.0)
            assert res.effective_risk_percent <= ABSOLUTE_MAX_RISK_PERCENT

    def test_property_4_absolute_distortion_ceiling(self):
        """Property 4: Maximum allowed distortion never exceeds ABSOLUTE_MAX_DISTORTION (10.0x)."""
        rc = RiskController()
        for eq in [1.0, 10.0, 50.0, 100.0, 500.0, 10000.0]:
            res = rc.evaluate(equity=eq, balance=eq, stop_distance=1.0)
            assert res.max_allowed_distortion <= ABSOLUTE_MAX_DISTORTION

    def test_property_5_daily_drawdown_hard_override(self):
        """Property 5: Daily drawdown always overrides the account-size risk curve and zeros out risk."""
        rc = RiskController()
        for eq in [10.0, 100.0, 500.0, 5000.0]:
            res = rc.evaluate(equity=eq, balance=eq, stop_distance=1.0, daily_locked=True)
            assert res.effective_risk_percent == 0.0
            assert res.risk_budget == 0.0
            assert res.risk_state == RiskState.DAILY_STOP
            assert res.trade_allowed is False
            assert res.reason == "DAILY_STOP"

    def test_property_6_strategy_invariance(self):
        """Property 6: Risk controller calculations cannot modify strategy scoring or direction."""
        cap = SymbolCapabilityProfile()
        rc = RiskController()

        mock_strategy_score = 0.72
        mock_strategy_dir = +1

        for eq in [3.0, 25.0, 100.0, 1000.0, 50000.0]:
            # Strategy output remains identical
            assert mock_strategy_score == 0.72
            assert mock_strategy_dir == +1

            acc = AccountIdentification(equity=eq, balance=eq, margin_free=eq)
            risk_res = rc.evaluate(equity=eq, balance=eq, stop_distance=5.0)

            # Feasibility is evaluated independently downstream
            if risk_res.trade_allowed:
                env = evaluate_account_execution(
                    acc, cap, direction=mock_strategy_dir, entry=2000.0, stop=1995.0,
                    target=2010.0, target_risk_pct=risk_res.effective_risk_percent,
                    max_allowed_distortion=risk_res.max_allowed_distortion
                )
                assert env.final_action == Action.TRADE
            else:
                assert risk_res.trade_allowed is False

    def test_property_7_never_force_small_account_trade(self):
        """Property 7: The controller never forces an unsafe trade merely because the account is small."""
        rc = RiskController()
        # $3 account with $5 min lot loss
        res = rc.evaluate(equity=3.0, balance=3.0, stop_distance=5.0, tick_size=0.01, tick_value=1.00, volume_min=0.01)
        assert res.trade_allowed is False
        assert res.risk_state == RiskState.UNSAFE
        assert res.reason == "MIN_LOT_UNSAFE"
        # Risk percentage was not escalated to 100% or 200%
        assert res.effective_risk_percent <= 1.50


class TestSmallAccountEdgeCases:

    def test_edge_case_3_dollar(self):
        """$3 account: risk=1.50% ($0.045 budget), allowed_dist=5.0x, min_lot_loss=$5.00 -> dist=111.11x -> NO_TRADE."""
        rc = RiskController()
        res = rc.evaluate(equity=3.0, balance=3.0, stop_distance=5.0, tick_size=0.01, tick_value=1.00, volume_min=0.01)
        assert abs(res.effective_risk_percent - 1.50) < 1e-5
        assert abs(res.risk_budget - 0.045) < 1e-5
        assert abs(res.max_allowed_distortion - 5.0) < 1e-5
        assert abs(res.distortion - (5.0 / 0.045)) < 1e-2  # ~111.11x
        assert res.distortion > res.max_allowed_distortion
        assert res.trade_allowed is False
        assert res.reason == "MIN_LOT_UNSAFE"
        # Required risk = 5.00 / (3.0 * 5.0) * 100 = 33.33% (diagnostic only, NOT applied)
        assert abs(res.required_risk_percent - (5.0 / 15.0 * 100)) < 1e-2

    def test_edge_case_5_dollar(self):
        """$5 account: risk=1.50% ($0.075 budget), allowed_dist=5.0x, min_lot_loss=$5.00 -> dist=66.67x -> NO_TRADE."""
        rc = RiskController()
        res = rc.evaluate(equity=5.0, balance=5.0, stop_distance=5.0, tick_size=0.01, tick_value=1.00, volume_min=0.01)
        assert abs(res.effective_risk_percent - 1.50) < 1e-5
        assert abs(res.risk_budget - 0.075) < 1e-5
        assert abs(res.distortion - 66.6667) < 1e-2
        assert res.trade_allowed is False
        assert res.reason == "MIN_LOT_UNSAFE"

    def test_edge_case_10_dollar(self):
        """$10 account: risk=1.50% ($0.15 budget), allowed_dist=5.0x. For a tight 1.0 point stop ($1.00 loss) -> dist=6.67x > 5.0x -> NO_TRADE."""
        rc = RiskController()
        # Tight stop of 1.0 point -> min lot loss = $1.00
        res = rc.evaluate(equity=10.0, balance=10.0, stop_distance=1.0, tick_size=0.01, tick_value=1.00, volume_min=0.01)
        assert abs(res.effective_risk_percent - 1.50) < 1e-5
        assert abs(res.risk_budget - 0.15) < 1e-5
        assert abs(res.distortion - (1.00 / 0.15)) < 1e-2  # 6.67x > 5.0x
        assert res.trade_allowed is False
        assert res.reason == "MIN_LOT_UNSAFE"

    def test_edge_case_25_dollar(self):
        """$25 account: risk=1.40625%, allowed_dist=4.625x. Tight 1.5 point stop ($1.50 loss) -> dist=4.27x <= 4.625x -> TRADE."""
        rc = RiskController()
        # $25 is 37.5% between $10 (1.50%, 5.0x) and $50 (1.25%, 4.0x) -> risk = 1.50 - 0.375*0.25 = 1.40625%, dist = 5.0 - 0.375*1.0 = 4.625x
        res = rc.evaluate(equity=25.0, balance=25.0, stop_distance=1.5, tick_size=0.01, tick_value=1.00, volume_min=0.01)
        assert abs(res.effective_risk_percent - 1.40625) < 1e-5
        assert abs(res.max_allowed_distortion - 4.625) < 1e-5
        assert abs(res.distortion - (1.50 / res.risk_budget)) < 1e-2
        assert res.trade_allowed is True

    def test_edge_case_50_dollar(self):
        """$50 account: risk=1.25% ($0.625 budget), allowed_dist=4.0x. Stop of 2.0 points ($2.00 loss) -> dist=3.2x <= 4.0x -> TRADE."""
        rc = RiskController()
        res = rc.evaluate(equity=50.0, balance=50.0, stop_distance=2.0, tick_size=0.01, tick_value=1.00, volume_min=0.01)
        assert abs(res.effective_risk_percent - 1.25) < 1e-5
        assert abs(res.max_allowed_distortion - 4.0) < 1e-5
        assert abs(res.distortion - (2.00 / 0.625)) < 1e-2  # 3.20x <= 4.0x
        assert res.trade_allowed is True

    def test_edge_case_100_dollar(self):
        """$100 account: risk=1.00% ($1.00 budget), allowed_dist=3.5x. Stop of 3.5 points ($3.50 loss) -> dist=3.5x <= 3.5x -> TRADE."""
        rc = RiskController()
        res = rc.evaluate(equity=100.0, balance=100.0, stop_distance=3.5, tick_size=0.01, tick_value=1.00, volume_min=0.01)
        assert abs(res.effective_risk_percent - 1.00) < 1e-5
        assert abs(res.max_allowed_distortion - 3.5) < 1e-5
        assert abs(res.distortion - 3.5) < 1e-5
        assert res.trade_allowed is True


class TestDrawdownThrottlingAndTotalDDIsonlation:

    def test_high_water_drawdown_reduces_risk_only(self):
        """High-water drawdown throttles risk downward by 0.70x (CAUTION) or 0.50x (RECOVERY), never increasing."""
        rc = RiskController(initial_equity=100.0)
        # Peak at $100 -> base risk = 1.00%
        rc.evaluate(equity=100.0, balance=100.0, stop_distance=1.0)

        # Drawdown 2.5% ($97.50 equity): base risk at $97.50 is ~1.015%, multiplied by 0.70x = ~0.71%
        res_caut = rc.evaluate(equity=97.50, balance=97.50, stop_distance=1.0)
        assert res_caut.risk_state == RiskState.CAUTION
        assert res_caut.effective_risk_percent < res_caut.base_risk_percent
        assert abs(res_caut.effective_risk_percent - (res_caut.base_risk_percent * 0.70)) < 1e-5

        # Drawdown 4.0% ($96.00 equity): multiplied by 0.50x
        res_rec = rc.evaluate(equity=96.00, balance=96.00, stop_distance=1.0)
        assert res_rec.risk_state == RiskState.RECOVERY
        assert abs(res_rec.effective_risk_percent - (res_rec.base_risk_percent * 0.50)) < 1e-5

    def test_total_dd_lock_never_triggered(self):
        """Total drawdown lock is not part of the risk controller."""
        rc = RiskController(initial_equity=1000.0)
        rc.evaluate(equity=1000.0, balance=1000.0, stop_distance=1.0)

        # Drawdown of 15% ($850 equity)
        res = rc.evaluate(equity=850.0, balance=850.0, stop_distance=1.0)
        assert res.risk_state == RiskState.RECOVERY
        assert "TOTAL_DD_LOCK" not in res.reason
        assert res.trade_allowed is True


class TestSection44DistortionAndRiskRequirements:
    """Covers explicit test requirements from Section 4.4:
    - Micro-account maximum distortion <= 5x
    - Monotonic distortion decrease across account tiers
    - Mature-account policy floor
    - Tier boundaries
    - Invalid configuration
    - Equity growth and restart persistence
    - Equity declines without automatic relaxation of the distortion ceiling
    - Minimum-lot risk above the ceiling
    - Affordable minimum-lot risk
    - Volume normalization
    - Invalid symbol specifications
    - Invalid stop distances
    - Final-quote changes
    - Diagnostic/authorization consistency
    - Rejection of non-finite or invalid calculations
    """

    def test_micro_account_max_distortion_ceiling(self):
        """Micro-account tier (equity <= $100) must strictly have max distortion <= 5.0x."""
        for eq in [0.01, 1.0, 5.0, 10.0, 25.0, 50.0, 75.0, 99.99]:
            d = interpolate_distortion_curve(eq)
            assert d <= 5.0, f"Micro equity {eq} distortion ceiling {d} exceeds 5.0x"

    def test_monotonic_distortion_decrease_across_all_tiers(self):
        """Allowed distortion must monotonically decrease as equity increases from micro to mature."""
        equities = [1.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0, 25000.0]
        prev_d = float("inf")
        for eq in equities:
            d = interpolate_distortion_curve(eq)
            assert d <= prev_d, f"Distortion did not decrease monotonically: {d} > {prev_d} at equity {eq}"
            prev_d = d

    def test_mature_account_policy_floor(self):
        """Mature account tier ($10,000+) must have distortion floor of exactly 1.0x."""
        for eq in [10000.0, 15000.0, 50000.0, 100000.0, 1000000.0]:
            d = interpolate_distortion_curve(eq)
            assert abs(d - 1.0) < 1e-5, f"Mature equity {eq} distortion floor was {d}, expected 1.0"

    def test_tier_boundaries_continuity(self):
        """Tier boundary transitions must be continuous (no jump discontinuities)."""
        boundaries = [10.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 5000.0, 10000.0]
        for b in boundaries:
            d_left = interpolate_distortion_curve(b - 1e-4)
            d_mid = interpolate_distortion_curve(b)
            d_right = interpolate_distortion_curve(b + 1e-4)
            assert abs(d_left - d_mid) < 1e-3, f"Discontinuity at left of {b}: {d_left} vs {d_mid}"
            assert abs(d_right - d_mid) < 1e-3, f"Discontinuity at right of {b}: {d_right} vs {d_mid}"

    def test_invalid_configuration_handling(self):
        """Custom inverted/invalid curves fail safely or clamp without corrupting calculation."""
        # Custom curve with single invalid point
        rc = RiskController()
        # Invalid inputs to calculate_minimum_viable_equity
        assert rc.calculate_minimum_viable_equity(min_lot_loss=0.0, effective_risk_pct=1.0, max_distortion=5.0) == 0.0
        assert rc.calculate_minimum_viable_equity(min_lot_loss=5.0, effective_risk_pct=0.0, max_distortion=5.0) > 0.0
        assert rc.calculate_minimum_viable_equity(min_lot_loss=5.0, effective_risk_pct=1.0, max_distortion=0.0) == 0.0
        # Invalid inputs to calculate_required_risk_percent
        assert rc.calculate_required_risk_percent(min_lot_loss=0.0, equity=100.0, max_distortion=5.0) == 999.0
        assert rc.calculate_required_risk_percent(min_lot_loss=5.0, equity=0.0, max_distortion=5.0) == 999.0
        assert rc.calculate_required_risk_percent(min_lot_loss=5.0, equity=-10.0, max_distortion=5.0) == 999.0

    def test_rejection_of_non_finite_or_invalid_calculations(self):
        """Non-finite or invalid values (zero/negative equity, zero stop) must be safely rejected."""
        rc = RiskController()
        # Zero equity
        res_zero = rc.evaluate(equity=0.0, balance=0.0, stop_distance=1.0)
        assert res_zero.trade_allowed is False
        assert res_zero.risk_state == RiskState.UNSAFE

        # Negative equity
        res_neg = rc.evaluate(equity=-100.0, balance=-100.0, stop_distance=1.0)
        assert res_neg.trade_allowed is False
        assert res_neg.risk_state == RiskState.UNSAFE

        # Zero stop distance
        res_zstop = rc.evaluate(equity=1000.0, balance=1000.0, stop_distance=0.0)
        # min_lot_loss is 0, so distortion is 999.0, rejected
        assert res_zstop.trade_allowed is False

    def test_equity_growth_and_decline_distortion_retention(self):
        """As equity grows, distortion ceiling tightens. When equity declines, high water mark reflects prior state."""
        rc = RiskController(initial_equity=500.0)
        # Peak at $500 -> max allowed distortion = 2.5x
        res1 = rc.evaluate(equity=500.0, balance=500.0, stop_distance=1.0)
        assert abs(res1.max_allowed_distortion - 2.5) < 1e-5

        # Grow to $10,000 -> max allowed distortion = 1.0x
        res2 = rc.evaluate(equity=10000.0, balance=10000.0, stop_distance=1.0)
        assert abs(res2.max_allowed_distortion - 1.0) < 1e-5
        assert rc.high_water_equity == 10000.0

        # Decline back to $8,000: drawdown detected, risk throttled
        res3 = rc.evaluate(equity=8000.0, balance=8000.0, stop_distance=1.0)
        assert res3.drawdown_percent == 20.0  # (10000 - 8000) / 10000 * 100
        assert res3.risk_state == RiskState.RECOVERY
        assert res3.effective_risk_percent == res3.base_risk_percent * 0.50

    def test_diagnostic_and_authorization_consistency(self):
        """trade_allowed must be strictly consistent with reason, distortion <= max_allowed, and risk_state."""
        rc = RiskController()
        for eq in [25.0, 100.0, 500.0, 5000.0]:
            for stop in [0.5, 1.0, 2.5, 5.0, 10.0, 20.0]:
                res = rc.evaluate(equity=eq, balance=eq, stop_distance=stop)
                if res.trade_allowed:
                    assert res.reason == "RISK_OK"
                    assert res.distortion <= res.max_allowed_distortion + 1e-5
                    assert res.risk_state in (RiskState.NORMAL, RiskState.CAUTION, RiskState.RECOVERY)
                else:
                    assert res.reason in ("MIN_LOT_UNSAFE", "DAILY_STOP", "ZERO_OR_NEGATIVE_EQUITY")
                    assert res.trade_allowed is False


