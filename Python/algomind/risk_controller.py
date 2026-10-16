"""AMIGO Account-Size-Correlated Risk + Distortion Engine (Python Mirror).

Implements the deterministic RiskController component matching MQL5 RiskController.mqh:
  - Account-size risk spline curve (1.50% at $10 -> 0.50% at $500+)
  - Account-size distortion spline curve (8.0x at $10 -> 1.0x at $10,000)
  - Piecewise-linear interpolation with upper/lower clamping
  - Absolute hard safety ceilings (ABSOLUTE_MAX_RISK_PERCENT = 2.0%, ABSOLUTE_MAX_DISTORTION = 10.0x)
  - Informational high-water drawdown calculation and throttle multiplier (downward only: <2% 1.0x, 2-3.5% 0.70x, >=3.5% 0.50x)
  - Daily drawdown hard stop gate (DAILY_STOP: 0.00% -> NO_TRADE)
  - Broker minimum-lot feasibility check
  - Reverse feasibility diagnostic: RequiredRiskPercent (NEVER overrides permitted curve)
  - Minimum viable equity diagnostic calculation
  - Total-drawdown policy is strictly excluded
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple

from algomind.account_execution import AccountClass, classify_account

ABSOLUTE_MAX_RISK_PERCENT = 2.00
ABSOLUTE_MAX_DISTORTION = 10.00


class RiskState(Enum):
    NORMAL = 0
    CAUTION = 1
    RECOVERY = 2
    DAILY_STOP = 3
    UNSAFE = 4


@dataclass
class AdaptiveRiskResult:
    equity: float
    balance: float
    high_water_equity: float
    growth_percent: float
    drawdown_percent: float
    base_risk_percent: float
    effective_risk_percent: float
    risk_budget: float
    account_class: AccountClass
    risk_state: RiskState
    minimum_lot: float
    minimum_lot_loss: float
    distortion: float
    max_allowed_distortion: float
    required_risk_percent: float
    minimum_viable_equity: float
    trade_allowed: bool
    reason: str


# Spline Anchor Points (Equity, Risk %, Max Distortion) - Section 3 Approved Defaults
DEFAULT_RISK_CURVE: List[Tuple[float, float, float]] = [
    (10.0, 1.50, 8.0),
    (50.0, 1.25, 6.0),
    (100.0, 1.00, 5.0),
    (250.0, 0.75, 4.0),
    (500.0, 0.50, 3.0),
    (1000.0, 0.50, 2.0),
    (5000.0, 0.50, 1.5),
    (10000.0, 0.50, 1.0),
]


def interpolate_risk_curve(equity: float, curve: Optional[List[Tuple[float, float, float]]] = None) -> float:
    pts = curve if curve is not None else DEFAULT_RISK_CURVE
    if equity <= pts[0][0]:
        return pts[0][1]
    if equity >= pts[-1][0]:
        return pts[-1][1]

    for i in range(len(pts) - 1):
        x0, y0, _ = pts[i]
        x1, y1, _ = pts[i + 1]
        if x0 <= equity <= x1:
            t = (equity - x0) / (x1 - x0)
            r = y0 + t * (y1 - y0)
            return min(r, ABSOLUTE_MAX_RISK_PERCENT)

    return pts[-1][1]


def interpolate_distortion_curve(equity: float, curve: Optional[List[Tuple[float, float, float]]] = None) -> float:
    pts = curve if curve is not None else DEFAULT_RISK_CURVE
    if equity <= pts[0][0]:
        return pts[0][2]
    if equity >= pts[-1][0]:
        return pts[-1][2]

    for i in range(len(pts) - 1):
        x0, _, d0 = pts[i]
        x1, _, d1 = pts[i + 1]
        if x0 <= equity <= x1:
            t = (equity - x0) / (x1 - x0)
            d = d0 + t * (d1 - d0)
            return min(d, ABSOLUTE_MAX_DISTORTION)

    return pts[-1][2]


class RiskController:
    """Deterministic account-size-correlated risk and distortion engine."""

    def __init__(self, initial_equity: float = 0.0, curve: Optional[List[Tuple[float, float, float]]] = None):
        self.initial_equity = max(0.0, initial_equity)
        self.high_water_equity = max(0.0, initial_equity)
        self.last_equity = max(0.0, initial_equity)
        self.curve = curve if curve is not None else DEFAULT_RISK_CURVE
        self.initialized = initial_equity > 0.0

    def init_equity(self, equity: float) -> None:
        if equity > 0:
            self.initial_equity = equity
            self.high_water_equity = equity
            self.last_equity = equity
            self.initialized = True

    def update(self, current_equity: float) -> None:
        if not self.initialized and current_equity > 0:
            self.init_equity(current_equity)
            return

        self.last_equity = current_equity
        if current_equity > self.high_water_equity:
            self.high_water_equity = current_equity

    @staticmethod
    def calculate_minimum_viable_equity(min_lot_loss: float, effective_risk_pct: float, max_distortion: float) -> float:
        r_dec = (effective_risk_pct / 100.0) if effective_risk_pct > 0 else 0.005
        denom = r_dec * max_distortion
        if denom <= 0.0 or min_lot_loss <= 0.0:
            return 0.0
        return min_lot_loss / denom

    @staticmethod
    def calculate_required_risk_percent(min_lot_loss: float, equity: float, max_distortion: float) -> float:
        denom = equity * max_distortion
        if denom <= 0.0 or min_lot_loss <= 0.0:
            return 999.0
        return (min_lot_loss / denom) * 100.0

    def evaluate(
        self,
        equity: float,
        balance: float,
        stop_distance: float,
        tick_size: float = 0.01,
        tick_value: float = 1.00,
        volume_min: float = 0.01,
        daily_locked: bool = False,
    ) -> AdaptiveRiskResult:
        self.update(equity)

        acc_class = classify_account(equity)

        # Growth from initial
        if self.initial_equity > 0.0:
            growth_pct = (equity - self.initial_equity) / self.initial_equity * 100.0
        else:
            growth_pct = 0.0

        # Drawdown from high-water mark (informational / throttle input only)
        if self.high_water_equity > 0.0 and equity < self.high_water_equity:
            dd_pct = (self.high_water_equity - equity) / self.high_water_equity * 100.0
        else:
            dd_pct = 0.0

        # 1. Derive Account-Size Baseline Risk % & Max Distortion from Spline Curves
        base_risk_pct = interpolate_risk_curve(equity, self.curve)
        max_allowed_dist = min(interpolate_distortion_curve(equity, self.curve), ABSOLUTE_MAX_DISTORTION)

        # Broker minimum-lot economics
        risk_per_lot = (stop_distance / tick_size) * tick_value if tick_size > 0 and stop_distance > 0 else 0.0
        min_lot_loss = volume_min * risk_per_lot

        # Diagnostics: Required Risk % and Initial Minimum Viable Equity
        req_risk_pct = self.calculate_required_risk_percent(min_lot_loss, equity, max_allowed_dist)
        mve = self.calculate_minimum_viable_equity(min_lot_loss, base_risk_pct, max_allowed_dist)

        # 2. Active Hard Account-Loss Control: DAILY DRAWDOWN
        if daily_locked:
            return AdaptiveRiskResult(
                equity=equity,
                balance=balance,
                high_water_equity=self.high_water_equity,
                growth_percent=growth_pct,
                drawdown_percent=dd_pct,
                base_risk_percent=base_risk_pct,
                effective_risk_percent=0.0,
                risk_budget=0.0,
                account_class=acc_class,
                risk_state=RiskState.DAILY_STOP,
                minimum_lot=volume_min,
                minimum_lot_loss=min_lot_loss,
                distortion=999.0,
                max_allowed_distortion=max_allowed_dist,
                required_risk_percent=req_risk_pct,
                minimum_viable_equity=mve,
                trade_allowed=False,
                reason="DAILY_STOP",
            )

        # Fail closed on zero or negative equity
        if equity <= 0.0:
            return AdaptiveRiskResult(
                equity=equity,
                balance=balance,
                high_water_equity=self.high_water_equity,
                growth_percent=growth_pct,
                drawdown_percent=dd_pct,
                base_risk_percent=base_risk_pct,
                effective_risk_percent=0.0,
                risk_budget=0.0,
                account_class=acc_class,
                risk_state=RiskState.UNSAFE,
                minimum_lot=volume_min,
                minimum_lot_loss=min_lot_loss,
                distortion=999.0,
                max_allowed_distortion=max_allowed_dist,
                required_risk_percent=req_risk_pct,
                minimum_viable_equity=mve,
                trade_allowed=False,
                reason="ZERO_OR_NEGATIVE_EQUITY",
            )

        # 3. High-Water Drawdown Throttle Multiplier (Drawdown may ONLY reduce risk, never increase it)
        if dd_pct >= 3.5:
            dd_mult = 0.50
            risk_state = RiskState.RECOVERY
        elif dd_pct >= 2.0:
            dd_mult = 0.70
            risk_state = RiskState.CAUTION
        else:
            dd_mult = 1.00
            risk_state = RiskState.NORMAL

        throttled_risk = base_risk_pct * dd_mult
        effective_risk_pct = min(throttled_risk, ABSOLUTE_MAX_RISK_PERCENT)

        # Update Minimum Viable Equity with effective risk percent
        mve = self.calculate_minimum_viable_equity(min_lot_loss, effective_risk_pct, max_allowed_dist)

        # 4. Compute Dollar Risk Budget
        risk_budget = equity * (effective_risk_pct / 100.0)

        # 5. Actual Distortion Calculation
        if risk_budget > 0.0 and min_lot_loss > 0.0:
            distortion = min_lot_loss / risk_budget
        else:
            distortion = 999.0

        # 6. Strict Account-Size Distortion Feasibility Gate (Section 8, 9, 14)
        if distortion > (max_allowed_dist + 1e-5):
            return AdaptiveRiskResult(
                equity=equity,
                balance=balance,
                high_water_equity=self.high_water_equity,
                growth_percent=growth_pct,
                drawdown_percent=dd_pct,
                base_risk_percent=base_risk_pct,
                effective_risk_percent=effective_risk_pct,
                risk_budget=risk_budget,
                account_class=acc_class,
                risk_state=RiskState.UNSAFE,
                minimum_lot=volume_min,
                minimum_lot_loss=min_lot_loss,
                distortion=distortion,
                max_allowed_distortion=max_allowed_dist,
                required_risk_percent=req_risk_pct,
                minimum_viable_equity=mve,
                trade_allowed=False,
                reason="MIN_LOT_UNSAFE",
            )

        return AdaptiveRiskResult(
            equity=equity,
            balance=balance,
            high_water_equity=self.high_water_equity,
            growth_percent=growth_pct,
            drawdown_percent=dd_pct,
            base_risk_percent=base_risk_pct,
            effective_risk_percent=effective_risk_pct,
            risk_budget=risk_budget,
            account_class=acc_class,
            risk_state=risk_state,
            minimum_lot=volume_min,
            minimum_lot_loss=min_lot_loss,
            distortion=distortion,
            max_allowed_distortion=max_allowed_dist,
            required_risk_percent=req_risk_pct,
            minimum_viable_equity=mve,
            trade_allowed=True,
            reason="RISK_OK",
        )
