"""AlgoMind Account-Aware Execution Layer (Python Engine & Simulation Core).

Implements the deterministic Account-Aware Execution Layer matching MQL5 Account Execution Engine:
  - Account Identification & Classification
  - Runtime Symbol Capability Profile & Contract-Spec Validation
  - 3-State Minimum-Lot Handling (NORMAL, MIN_LOT_ACCOMMODATED, MIN_LOT_UNSAFE)
  - Risk Sizing, Actual Risk, and Risk Distortion Calculation
  - Account Execution Feasibility & Final Action Resolution
  - Small-Account Simulation & Minimum Viable Account Analysis
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple


class AccountClass(Enum):
    UNKNOWN = 0
    MICRO = 1
    SMALL = 2
    STANDARD = 3
    LARGE = 4
    PROP = 5


class MinLotStatus(Enum):
    NORMAL = 0
    MIN_LOT_ACCOMMODATED = 1
    MIN_LOT_UNSAFE = 2


class FeasibilityStatus(Enum):
    NORMAL = 0
    MIN_LOT_ACCOMMODATED = 1
    MIN_LOT_UNSAFE = 2
    MARGIN_BLOCKED = 3
    BROKER_BLOCKED = 4
    INVALID_SYMBOL_SPEC = 5
    RISK_LIMIT_BLOCKED = 6
    STOPS_INVALID = 7


class Action(Enum):
    TRADE = 1
    REDUCE = 2
    WAIT = 3
    NO_TRADE = 4


@dataclass
class AccountIdentification:
    login: int = 100001
    broker: str = "Exness"
    server: str = "Exness-MT5Trial"
    currency: str = "USD"
    balance: float = 1000.0
    equity: float = 1000.0
    margin: float = 0.0
    margin_free: float = 1000.0
    margin_level: float = 0.0
    leverage: float = 500.0
    trade_allowed: bool = True
    trade_expert: bool = True
    account_class: AccountClass = AccountClass.STANDARD


@dataclass
class SymbolCapabilityProfile:
    symbol: str = "XAUUSDm"
    digits: int = 2
    point: float = 0.01
    tick_size: float = 0.01
    tick_value: float = 1.00  # $1.00 per 0.01 tick on 1.00 lot (contract size 100 oz)
    tick_value_profit: float = 1.00
    tick_value_loss: float = 1.00
    contract_size: float = 100.0
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01
    stops_level: int = 0
    freeze_level: int = 0
    trade_mode: int = 0  # 0=Full
    filling_mode: int = 1
    valid: bool = True
    invalid_reason: str = ""


@dataclass
class AccountExecutionEnvelope:
    account: AccountIdentification
    symbol_cap: SymbolCapabilityProfile
    direction: int
    entry: float
    stop: float
    target: float
    stop_distance: float
    target_risk_pct: float
    target_risk_amount: float
    risk_per_lot: float
    raw_volume: float
    executable_volume: float
    actual_risk: float
    actual_risk_pct: float
    risk_distortion: float
    required_margin: float
    min_lot_status: MinLotStatus
    feasibility: FeasibilityStatus
    final_action: Action
    reason: str
    diagnostics: List[str] = field(default_factory=list)


def validate_symbol_capability(cap: SymbolCapabilityProfile) -> Tuple[bool, str]:
    """Validate runtime symbol contract specification (Prompt §6)."""
    if cap.tick_size <= 0.0:
        return False, "INVALID_TICK_SIZE"
    if cap.tick_value <= 0.0:
        return False, "INVALID_TICK_VALUE"
    if cap.contract_size <= 0.0:
        return False, "INVALID_CONTRACT_SIZE"
    if cap.volume_min <= 0.0:
        return False, "INVALID_VOLUME_MIN"
    if cap.volume_step <= 0.0:
        return False, "INVALID_VOLUME_STEP"
    if cap.volume_max < cap.volume_min:
        return False, "INVALID_VOLUME_MAX"
    if cap.digits < 0:
        return False, "INVALID_DIGITS"
    if cap.point <= 0.0:
        return False, "INVALID_POINT"
    return True, "OK"


def classify_account(equity: float) -> AccountClass:
    """Classify operational account category (Thresholds: REQUIRES DECISION)."""
    if equity < 100.0:
        return AccountClass.MICRO
    elif equity < 1000.0:
        return AccountClass.SMALL
    elif equity < 10000.0:
        return AccountClass.STANDARD
    else:
        return AccountClass.LARGE


def evaluate_account_execution(
    account: AccountIdentification,
    symbol_cap: SymbolCapabilityProfile,
    direction: int,
    entry: float,
    stop: float,
    target: float,
    target_risk_pct: float = 0.5,
    max_allowed_distortion: float = 5.0,
    allow_min_lot_override: bool = True,
    strategy_action: Action = Action.TRADE,
) -> AccountExecutionEnvelope:
    """Evaluates execution feasibility, risk sizing, 3-state min lot handling, and produces structured diagnostics."""
    diagnostics = []
    stop_distance = abs(entry - stop)
    
    account.account_class = classify_account(account.equity)

    env = AccountExecutionEnvelope(
        account=account,
        symbol_cap=symbol_cap,
        direction=direction,
        entry=entry,
        stop=stop,
        target=target,
        stop_distance=stop_distance,
        target_risk_pct=target_risk_pct,
        target_risk_amount=0.0,
        risk_per_lot=0.0,
        raw_volume=0.0,
        executable_volume=0.0,
        actual_risk=0.0,
        actual_risk_pct=0.0,
        risk_distortion=1.0,
        required_margin=0.0,
        min_lot_status=MinLotStatus.NORMAL,
        feasibility=FeasibilityStatus.NORMAL,
        final_action=Action.NO_TRADE,
        reason="UNINITIALIZED",
        diagnostics=diagnostics,
    )

    # 1. Symbol Spec Validation
    valid_spec, spec_err = validate_symbol_capability(symbol_cap)
    if not valid_spec:
        env.feasibility = FeasibilityStatus.INVALID_SYMBOL_SPEC
        env.final_action = Action.NO_TRADE
        env.reason = f"INVALID_SYMBOL_SPEC:{spec_err}"
        return env

    # 2. Account Broker Permission Check
    if not account.trade_allowed or not account.trade_expert:
        env.feasibility = FeasibilityStatus.BROKER_BLOCKED
        env.final_action = Action.NO_TRADE
        env.reason = "BROKER_TRADE_DISABLED"
        return env

    # 3. Strategy Gate Respect
    if strategy_action != Action.TRADE:
        env.final_action = strategy_action
        env.reason = "STRATEGY_NOT_TRADE"
        return env

    # 4. Geometry Check
    if stop_distance <= 0.0:
        env.feasibility = FeasibilityStatus.STOPS_INVALID
        env.final_action = Action.NO_TRADE
        env.reason = "ZERO_STOP_DISTANCE"
        return env

    min_stop_dist = symbol_cap.stops_level * symbol_cap.point
    if min_stop_dist > 0.0 and stop_distance < min_stop_dist:
        env.feasibility = FeasibilityStatus.STOPS_INVALID
        env.final_action = Action.NO_TRADE
        env.reason = "STOP_BELOW_STOPS_LEVEL"
        return env

    # 5. Risk Sizing & 3-State Minimum Lot Sizing
    env.target_risk_amount = account.equity * (target_risk_pct / 100.0)
    env.risk_per_lot = (stop_distance / symbol_cap.tick_size) * symbol_cap.tick_value

    if env.risk_per_lot <= 0.0:
        env.feasibility = FeasibilityStatus.INVALID_SYMBOL_SPEC
        env.final_action = Action.NO_TRADE
        env.reason = "ZERO_RISK_PER_LOT"
        return env

    env.raw_volume = env.target_risk_amount / env.risk_per_lot

    # 3-State Minimum Lot Handling
    if env.raw_volume >= symbol_cap.volume_min:
        # STATE A: NORMAL
        env.min_lot_status = MinLotStatus.NORMAL
        raw_steps = math.floor(env.raw_volume / symbol_cap.volume_step)
        env.executable_volume = round(raw_steps * symbol_cap.volume_step, 4)
        if env.executable_volume < symbol_cap.volume_min:
            env.executable_volume = symbol_cap.volume_min
        if env.executable_volume > symbol_cap.volume_max:
            env.executable_volume = symbol_cap.volume_max

        env.actual_risk = env.executable_volume * env.risk_per_lot
        env.actual_risk_pct = (env.actual_risk / account.equity * 100.0) if account.equity > 0 else 0.0
        env.risk_distortion = (env.actual_risk / env.target_risk_amount) if env.target_risk_amount > 0 else 1.0
        env.feasibility = FeasibilityStatus.NORMAL
    else:
        # Raw Volume < VolumeMin
        min_lot_risk = symbol_cap.volume_min * env.risk_per_lot
        min_lot_risk_pct = (min_lot_risk / account.equity * 100.0) if account.equity > 0 else 999.0
        distortion = (min_lot_risk / env.target_risk_amount) if env.target_risk_amount > 0 else 999.0

        if allow_min_lot_override and distortion <= max_allowed_distortion:
            # STATE B: MIN_LOT_ACCOMMODATED
            env.min_lot_status = MinLotStatus.MIN_LOT_ACCOMMODATED
            env.executable_volume = symbol_cap.volume_min
            env.actual_risk = min_lot_risk
            env.actual_risk_pct = min_lot_risk_pct
            env.risk_distortion = distortion
            env.feasibility = FeasibilityStatus.MIN_LOT_ACCOMMODATED
        else:
            # STATE C: MIN_LOT_UNSAFE
            env.min_lot_status = MinLotStatus.MIN_LOT_UNSAFE
            env.executable_volume = 0.0
            env.actual_risk = min_lot_risk
            env.actual_risk_pct = min_lot_risk_pct
            env.risk_distortion = distortion
            env.feasibility = FeasibilityStatus.MIN_LOT_UNSAFE
            env.final_action = Action.NO_TRADE
            env.reason = "MIN_LOT_UNSAFE"
            _build_diagnostics(env)
            return env

    # 6. Margin Verification
    leverage = account.leverage if account.leverage > 0 else 100.0
    env.required_margin = (env.executable_volume * symbol_cap.contract_size * entry) / leverage

    if account.margin_free > 0 and env.required_margin > account.margin_free * 0.95:
        env.feasibility = FeasibilityStatus.MARGIN_BLOCKED
        env.final_action = Action.NO_TRADE
        env.reason = "INSUFFICIENT_MARGIN"
        _build_diagnostics(env)
        return env

    # 7. Final Action Resolution
    env.final_action = Action.TRADE
    env.reason = "MIN_LOT_ACCOMMODATED" if env.min_lot_status == MinLotStatus.MIN_LOT_ACCOMMODATED else "OK"
    _build_diagnostics(env)

    return env


def _build_diagnostics(env: AccountExecutionEnvelope):
    """Format structured diagnostics matching Prompt §15."""
    cls_name = env.account.account_class.name
    min_lot_str = env.min_lot_status.name
    act_str = env.final_action.name

    env.diagnostics = [
        f"[ACCOUNT] equity={env.account.equity:.2f} balance={env.account.balance:.2f} free_margin={env.account.margin_free:.2f} leverage={env.account.leverage:.0f} class={cls_name} login={env.account.login}",
        f"[SYMBOL] symbol={env.symbol_cap.symbol} tick_sz={env.symbol_cap.tick_size:.5f} tick_val={env.symbol_cap.tick_value:.5f} contract_sz={env.symbol_cap.contract_size:.1f} vol_min={env.symbol_cap.volume_min:.2f} vol_step={env.symbol_cap.volume_step:.2f} stops_lvl={env.symbol_cap.stops_level}",
        f"[SETUP] dir={'BUY' if env.direction == 1 else 'SELL'} entry={env.entry:.5f} sl={env.stop:.5f} tp={env.target:.5f} stop_dist={env.stop_distance:.5f}",
        f"[RISK] target_risk=${env.target_risk_amount:.2f}({env.target_risk_pct:.2f}%) risk_per_lot=${env.risk_per_lot:.2f} raw_vol={env.raw_volume:.5f} exec_vol={env.executable_volume:.2f} actual_risk=${env.actual_risk:.2f}({env.actual_risk_pct:.2f}%) distortion={env.risk_distortion:.2f}x",
        f"[ACCOUNT_HANDLING] class={cls_name} status={env.feasibility.value} min_lot_status={min_lot_str} margin_req=${env.required_margin:.2f}",
        f"[FINAL_ACTION] action={act_str} reason={env.reason}",
    ]


import math
