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


class SignalExecutionClassification(Enum):
    SIGNAL_INVALID = 0
    SIGNAL_VALID_EXECUTABLE = 1
    SIGNAL_VALID_ACCOUNT_INFEASIBLE = 2
    SIGNAL_VALID_BROKER_INFEASIBLE = 3


class SymbolTradeMode(Enum):
    DISABLED = 0
    LONG_ONLY = 1
    SHORT_ONLY = 2
    CLOSE_ONLY = 3
    FULL = 4


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
    trade_mode: int = SymbolTradeMode.FULL.value  # 4 = SYMBOL_TRADE_MODE_FULL per MT5 C++ API
    filling_mode: int = 1
    valid: bool = True
    invalid_reason: str = ""


class SLAdaptationStatus(Enum):
    ORIGINAL_SL_EXECUTABLE = 0
    ADAPTIVE_SL_REQUIRED = 1
    ADAPTIVE_SL_ACCEPTED = 2
    ADAPTIVE_SL_REJECTED = 3
    NO_VALID_SL = 4


@dataclass
class AdaptiveSLResult:
    status: SLAdaptationStatus
    original_sl: float
    original_stop_dist: float
    max_account_stop_dist: float
    candidate_sl: float
    candidate_stop_dist: float
    selected_sl: float
    selected_stop_dist: float
    rr: float
    reason: str


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
    original_sl: float = 0.0
    original_stop_distance: float = 0.0
    adaptive_sl: float = 0.0
    selected_sl: float = 0.0
    max_account_stop_dist: float = 0.0
    sl_adapt_status: SLAdaptationStatus = SLAdaptationStatus.ORIGINAL_SL_EXECUTABLE
    sl_adapt_reason: str = ""
    min_lot_status: MinLotStatus = MinLotStatus.NORMAL
    feasibility: FeasibilityStatus = FeasibilityStatus.NORMAL
    execution_classification: SignalExecutionClassification = SignalExecutionClassification.SIGNAL_INVALID
    final_action: Action = Action.NO_TRADE
    reason: str = "UNINITIALIZED"
    diagnostics: List[str] = field(default_factory=list)


def evaluate_adaptive_stop(
    symbol_cap: SymbolCapabilityProfile,
    equity: float,
    direction: int,
    entry: float,
    original_sl: float,
    target: float,
    structural_invalid: float = 0.0,
    atr: float = 0.0,
    target_risk_pct: float = 0.5,
    max_allowed_distortion: float = 5.0,
    min_rr_required: float = 2.0,
) -> AdaptiveSLResult:
    """Evaluates whether an adaptive stop-loss is required and selects a strategy-valid candidate."""
    original_stop_dist = abs(entry - original_sl)
    initial_rr = (abs(target - entry) / original_stop_dist) if original_stop_dist > 0 else 0.0

    res = AdaptiveSLResult(
        status=SLAdaptationStatus.NO_VALID_SL,
        original_sl=original_sl,
        original_stop_dist=original_stop_dist,
        max_account_stop_dist=0.0,
        candidate_sl=0.0,
        candidate_stop_dist=0.0,
        selected_sl=original_sl,
        selected_stop_dist=original_stop_dist,
        rr=initial_rr,
        reason="UNINITIALIZED",
    )

    if (
        symbol_cap.tick_size <= 0.0
        or symbol_cap.tick_value <= 0.0
        or symbol_cap.volume_min <= 0.0
        or equity <= 0.0
        or original_stop_dist <= 0.0
    ):
        res.status = SLAdaptationStatus.ADAPTIVE_SL_REJECTED
        res.reason = "INVALID_SYMBOL_OR_ACCOUNT_ECONOMICS"
        return res

    target_risk_amt = equity * (target_risk_pct / 100.0)
    max_risk_allowed = target_risk_amt * max_allowed_distortion
    val_per_unit = symbol_cap.tick_value / symbol_cap.tick_size
    res.max_account_stop_dist = max_risk_allowed / (symbol_cap.volume_min * val_per_unit)

    # 1. Is original SL executable?
    if original_stop_dist <= res.max_account_stop_dist:
        res.status = SLAdaptationStatus.ORIGINAL_SL_EXECUTABLE
        res.selected_sl = original_sl
        res.selected_stop_dist = original_stop_dist
        res.reason = "ORIGINAL_SL_EXECUTABLE"
        return res

    # 2. Adaptation REQUIRED
    res.status = SLAdaptationStatus.ADAPTIVE_SL_REQUIRED

    cand_a = 0.0
    cand_b = 0.0

    if direction == 1:
        if 0.0 < structural_invalid < entry and structural_invalid > original_sl:
            cand_a = structural_invalid
        if atr > 0.0:
            cand_b = entry - 1.0 * atr
    else:
        if structural_invalid > entry and (original_sl == 0.0 or structural_invalid < original_sl):
            cand_a = structural_invalid
        if atr > 0.0:
            cand_b = entry + 1.0 * atr

    candidates = [cand_a, cand_b]
    min_stop_dist = symbol_cap.stops_level * symbol_cap.point

    for idx, c_sl in enumerate(candidates):
        if c_sl <= 0.0:
            continue

        c_sl = round(c_sl, symbol_cap.digits)
        c_dist = abs(entry - c_sl)

        # Rule 1: Correct side of entry
        if direction == 1 and c_sl >= entry:
            continue
        if direction == -1 and c_sl <= entry:
            continue

        # Rule 2: Non-zero distance
        if c_dist <= 0.0:
            continue

        # Rule 3: Broker minimum stop distance
        if min_stop_dist > 0.0 and c_dist < min_stop_dist:
            continue

        # Rule 4: Must be within account-compatible maximum distance
        if c_dist > res.max_account_stop_dist:
            continue

        # Rule 5: Minimum RR requirement
        cand_rr = (abs(target - entry) / c_dist) if c_dist > 0 else 0.0
        if cand_rr < min_rr_required:
            continue

        res.status = SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED
        res.candidate_sl = c_sl
        res.candidate_stop_dist = c_dist
        res.selected_sl = c_sl
        res.selected_stop_dist = c_dist
        res.rr = cand_rr
        res.reason = "VALID_STRATEGY_STRUCTURE" if idx == 0 else "VALID_STRATEGY_ATR"
        return res

    res.status = SLAdaptationStatus.ADAPTIVE_SL_REJECTED
    res.selected_sl = original_sl
    res.selected_stop_dist = original_stop_dist
    res.reason = "NO_VALID_ADAPTIVE_SL"
    return res


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
    original_sl: float = 0.0,
    structural_invalid: float = 0.0,
    atr: float = 0.0,
) -> AccountExecutionEnvelope:
    """Evaluates execution feasibility, risk sizing, 3-state min lot handling, and produces structured diagnostics."""
    diagnostics = []
    
    # Evaluate Adaptive SL if original_sl provided and differs from stop
    orig_sl = original_sl if original_sl > 0 else stop
    adapt_res = evaluate_adaptive_stop(
        symbol_cap=symbol_cap,
        equity=account.equity,
        direction=direction,
        entry=entry,
        original_sl=orig_sl,
        target=target,
        structural_invalid=structural_invalid,
        atr=atr,
        target_risk_pct=target_risk_pct,
        max_allowed_distortion=max_allowed_distortion,
    )

    selected_stop = stop
    if adapt_res.status == SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED:
        selected_stop = adapt_res.selected_sl

    stop_distance = abs(entry - selected_stop)
    account.account_class = classify_account(account.equity)

    env = AccountExecutionEnvelope(
        account=account,
        symbol_cap=symbol_cap,
        direction=direction,
        entry=entry,
        stop=selected_stop,
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
        original_sl=orig_sl,
        original_stop_distance=abs(entry - orig_sl),
        adaptive_sl=adapt_res.candidate_sl,
        selected_sl=selected_stop,
        max_account_stop_dist=adapt_res.max_account_stop_dist,
        sl_adapt_status=adapt_res.status,
        sl_adapt_reason=adapt_res.reason,
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
        env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_BROKER_INFEASIBLE
        env.final_action = Action.NO_TRADE
        env.reason = f"INVALID_SYMBOL_SPEC:{spec_err}"
        return env

    # 2. Account Broker Permission Check
    if not account.trade_allowed or not account.trade_expert or symbol_cap.trade_mode == SymbolTradeMode.DISABLED.value:
        env.feasibility = FeasibilityStatus.BROKER_BLOCKED
        env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_BROKER_INFEASIBLE
        env.final_action = Action.NO_TRADE
        env.reason = "SYMBOL_TRADE_MODE_DISABLED" if symbol_cap.trade_mode == SymbolTradeMode.DISABLED.value else "BROKER_TRADE_DISABLED"
        return env

    # 3. Strategy Gate Respect
    if strategy_action != Action.TRADE:
        env.execution_classification = SignalExecutionClassification.SIGNAL_INVALID
        env.final_action = strategy_action
        env.reason = "STRATEGY_NOT_TRADE"
        return env

    # 4. Geometry Check
    if stop_distance <= 0.0:
        env.feasibility = FeasibilityStatus.STOPS_INVALID
        env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_BROKER_INFEASIBLE
        env.final_action = Action.NO_TRADE
        env.reason = "ZERO_STOP_DISTANCE"
        return env

    min_stop_dist = symbol_cap.stops_level * symbol_cap.point
    if min_stop_dist > 0.0 and stop_distance < min_stop_dist:
        env.feasibility = FeasibilityStatus.STOPS_INVALID
        env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_BROKER_INFEASIBLE
        env.final_action = Action.NO_TRADE
        env.reason = "STOP_BELOW_STOPS_LEVEL"
        return env

    # 5. Risk Sizing & 3-State Minimum Lot Sizing
    env.target_risk_amount = account.equity * (target_risk_pct / 100.0)
    env.risk_per_lot = (stop_distance / symbol_cap.tick_size) * symbol_cap.tick_value if symbol_cap.tick_size > 0 else 0.0

    if env.risk_per_lot <= 0.0:
        env.feasibility = FeasibilityStatus.INVALID_SYMBOL_SPEC
        env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_BROKER_INFEASIBLE
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
        env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_EXECUTABLE
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
            env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_EXECUTABLE
        else:
            # STATE C: MIN_LOT_UNSAFE
            env.min_lot_status = MinLotStatus.MIN_LOT_UNSAFE
            env.executable_volume = 0.0
            env.actual_risk = min_lot_risk
            env.actual_risk_pct = min_lot_risk_pct
            env.risk_distortion = distortion
            env.feasibility = FeasibilityStatus.MIN_LOT_UNSAFE
            env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_ACCOUNT_INFEASIBLE
            env.final_action = Action.NO_TRADE
            env.reason = "MIN_LOT_UNSAFE"
            _build_diagnostics(env, max_allowed_distortion)
            return env

    # 6. Margin Verification
    leverage = account.leverage if account.leverage > 0 else 100.0
    env.required_margin = (env.executable_volume * symbol_cap.contract_size * entry) / leverage

    if account.margin_free > 0 and env.required_margin > account.margin_free * 0.95:
        env.feasibility = FeasibilityStatus.MARGIN_BLOCKED
        env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_ACCOUNT_INFEASIBLE
        env.final_action = Action.NO_TRADE
        env.reason = "INSUFFICIENT_MARGIN"
        _build_diagnostics(env, max_allowed_distortion)
        return env

    # 7. Final Action Resolution
    env.execution_classification = SignalExecutionClassification.SIGNAL_VALID_EXECUTABLE
    env.final_action = Action.TRADE
    env.reason = "MIN_LOT_ACCOMMODATED" if env.min_lot_status == MinLotStatus.MIN_LOT_ACCOMMODATED else "OK"
    _build_diagnostics(env, max_allowed_distortion)

    return env


def _build_diagnostics(env: AccountExecutionEnvelope, max_allowed_distortion: float = 5.0):
    """Format structured diagnostics matching Prompt §15, §19 & REQ-07."""
    cls_name = env.account.account_class.name
    min_lot_str = env.min_lot_status.name
    act_str = env.final_action.name
    exec_class_str = env.execution_classification.name

    adapt_status_str = (
        "ORIGINAL_SL_EXECUTABLE" if env.sl_adapt_status == SLAdaptationStatus.ORIGINAL_SL_EXECUTABLE
        else "ADAPTIVE_SL_REQUIRED" if env.sl_adapt_status == SLAdaptationStatus.ADAPTIVE_SL_REQUIRED
        else "ACCEPTED" if env.sl_adapt_status == SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED
        else "REJECTED" if env.sl_adapt_status == SLAdaptationStatus.ADAPTIVE_SL_REJECTED
        else "NO_VALID_SL"
    )

    rr_val = (abs(env.target - env.entry) / env.stop_distance) if env.stop_distance > 0 else 0.0
    cand_dist = abs(env.entry - env.adaptive_sl) if env.adaptive_sl > 0 else 0.0

    sl_adapt_log = (
        f"[AlgoMind][SL_ADAPT] sym={env.symbol_cap.symbol} dir={'BUY' if env.direction == 1 else 'SELL'} "
        f"entry={env.entry:.5f} original_sl={env.original_sl:.5f} original_dist={env.original_stop_distance:.5f} "
        f"adaptive_required={1 if env.sl_adapt_status != SLAdaptationStatus.ORIGINAL_SL_EXECUTABLE else 0} "
        f"max_account_stop_dist={env.max_account_stop_dist:.5f} candidate_sl={env.adaptive_sl:.5f} "
        f"candidate_dist={cand_dist:.5f} selected_sl={env.selected_sl:.5f} rr={rr_val:.2f} "
        f"target_risk={env.target_risk_amount:.2f} actual_risk={env.actual_risk:.2f} "
        f"actual_risk_pct={env.actual_risk_pct:.2f} final_volume={env.executable_volume:.2f} "
        f"status={adapt_status_str} reason={env.sl_adapt_reason if env.sl_adapt_reason else env.reason}"
    )

    max_risk_allowed = env.target_risk_amount * max_allowed_distortion
    stop_dist_ticks = (env.stop_distance / env.symbol_cap.tick_size) if env.symbol_cap.tick_size > 0 else 0.0
    min_lot_loss = env.symbol_cap.volume_min * env.risk_per_lot
    target_risk_pct_dec = env.target_risk_pct / 100.0 if env.target_risk_pct > 0 else 0.005
    req_equity = (min_lot_loss / (target_risk_pct_dec * max_allowed_distortion)) if (target_risk_pct_dec * max_allowed_distortion) > 0 else 0.0
    broker_min_stop = env.symbol_cap.stops_level * env.symbol_cap.point
    sl_source_str = env.sl_adapt_reason if env.sl_adapt_status == SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED else "PRIMARY_STRUCTURE"
    cand_count = 2 if env.sl_adapt_status != SLAdaptationStatus.ORIGINAL_SL_EXECUTABLE else 1
    exec_cand_count = 1 if env.sl_adapt_status in (SLAdaptationStatus.ADAPTIVE_SL_ACCEPTED, SLAdaptationStatus.ORIGINAL_SL_EXECUTABLE) else 0

    size_diag_log = (
        f"[SIZE_DIAG] equity={env.account.equity:.2f} target_risk={env.target_risk_amount:.2f} max_risk={max_risk_allowed:.2f} "
        f"entry={env.entry:.5f} primary_sl={env.original_sl:.5f} selected_sl={env.selected_sl:.5f} sl_source={sl_source_str} "
        f"stop_dist_price={env.stop_distance:.5f} stop_dist_ticks={stop_dist_ticks:.0f} min_volume={env.symbol_cap.volume_min:.2f} "
        f"min_lot_loss={min_lot_loss:.2f} distortion={env.risk_distortion:.2f}x max_distortion={max_allowed_distortion:.2f}x "
        f"required_equity={req_equity:.2f} broker_min_stop={broker_min_stop:.5f} rr={rr_val:.2f} "
        f"candidate_count={cand_count} executable_candidate_count={exec_cand_count} classification={exec_class_str} reason={env.reason}"
    )

    env.diagnostics = [
        f"[ACCOUNT] equity={env.account.equity:.2f} balance={env.account.balance:.2f} free_margin={env.account.margin_free:.2f} leverage={env.account.leverage:.0f} class={cls_name} login={env.account.login}",
        f"[SYMBOL] symbol={env.symbol_cap.symbol} tick_sz={env.symbol_cap.tick_size:.5f} tick_val={env.symbol_cap.tick_value:.5f} contract_sz={env.symbol_cap.contract_size:.1f} vol_min={env.symbol_cap.volume_min:.2f} vol_step={env.symbol_cap.volume_step:.2f} stops_lvl={env.symbol_cap.stops_level}",
        f"[SETUP] dir={'BUY' if env.direction == 1 else 'SELL'} entry={env.entry:.5f} sl={env.stop:.5f} tp={env.target:.5f} stop_dist={env.stop_distance:.5f}",
        f"[RISK] target_risk=${env.target_risk_amount:.2f}({env.target_risk_pct:.2f}%) risk_per_lot=${env.risk_per_lot:.2f} raw_vol={env.raw_volume:.5f} exec_vol={env.executable_volume:.2f} actual_risk=${env.actual_risk:.2f}({env.actual_risk_pct:.2f}%) distortion={env.risk_distortion:.2f}x",
        f"[ACCOUNT_HANDLING] class={cls_name} status={env.feasibility.value} min_lot_status={min_lot_str} margin_req=${env.required_margin:.2f}",
        sl_adapt_log,
        size_diag_log,
        f"[FINAL_ACTION] action={act_str} classification={exec_class_str} reason={env.reason}",
    ]


import math
