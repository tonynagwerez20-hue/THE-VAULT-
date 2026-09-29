"""AlgoMind Position Manager - 50% Break-Even & Dynamic 25% Trailing Stop Module.

Implements the post-entry position management layer per Master Prompt requirements:
  - Sequence: ENTRY -> INITIAL SL/TP -> 50% TP PROGRESS -> BREAK-EVEN -> DYNAMIC 25% TRAILING -> PROTECTED EXIT
  - BUY Formula: Proposed SL = CurrentPrice - (CurrentPrice - Entry) * 0.25 = Entry + (CurrentPrice - Entry) * 0.75
  - SELL Formula: Proposed SL = CurrentPrice + (Entry - CurrentPrice) * 0.25 = Entry - (Entry - CurrentPrice) * 0.75
  - Ratchet Protection: Stop loss ONLY moves in the protective direction (BUY: strictly higher, SELL: strictly lower).
  - Symbol Precision & Broker Stops Level compliance.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple


class TrailingMode(Enum):
    OFF = 0
    DYNAMIC_25_PERCENT = 1
    ATR = 2
    STRUCTURE = 3
    ATR_PLUS_STRUCTURE = 4


class PositionDirection(Enum):
    BUY = 1
    SELL = -1


@dataclass
class SymbolInfo:
    symbol: str
    digits: int = 2
    point: float = 0.01
    tick_size: float = 0.01
    stops_level: float = 0.0   # in points
    freeze_level: float = 0.0  # in points


@dataclass
class PositionState:
    position_id: int
    symbol: str
    direction: PositionDirection
    entry: float
    initial_stop: float
    initial_target: float
    initial_atr: float
    initial_risk_per_unit: float
    partial_done: bool = False
    current_stop: float = 0.0
    be_activated: bool = False
    be_trigger_price: float = 0.0
    last_applied_stop: float = 0.0
    trailing_mode: TrailingMode = TrailingMode.DYNAMIC_25_PERCENT
    opened_time: float = 0.0
    is_closed: bool = False
    close_reason: Optional[str] = None
    logs: List[str] = field(default_factory=list)


def calculate_be_trigger_price(entry: float, target: float, direction: PositionDirection) -> float:
    """Calculate the Break-Even trigger price at 50% of Entry->TP distance."""
    tp_distance = abs(target - entry)
    be_trigger_distance = tp_distance * 0.50
    if direction == PositionDirection.BUY:
        return entry + be_trigger_distance
    else:
        return entry - be_trigger_distance


def calculate_25pct_trailing_sl(entry: float, current_price: float, direction: PositionDirection) -> float:
    """Calculate proposed trailing SL 25% behind current price from Entry."""
    if direction == PositionDirection.BUY:
        profit_distance = current_price - entry
        if profit_distance <= 0:
            return entry
        trailing_distance = profit_distance * 0.25
        return current_price - trailing_distance
    else:
        profit_distance = entry - current_price
        if profit_distance <= 0:
            return entry
        trailing_distance = profit_distance * 0.25
        return current_price + trailing_distance


class PositionManager:
    """Manages post-entry positions, break-even transitions, trailing stops, and exits."""

    def __init__(self, trailing_mode: TrailingMode = TrailingMode.DYNAMIC_25_PERCENT):
        self.trailing_mode = trailing_mode
        self.positions: Dict[int, PositionState] = {}

    def register_position(
        self,
        position_id: int,
        symbol: str,
        direction: PositionDirection,
        entry: float,
        initial_stop: float,
        initial_target: float,
        initial_atr: float,
        opened_time: float = 0.0,
        trailing_mode: Optional[TrailingMode] = None,
    ) -> PositionState:
        """Register a newly opened position."""
        risk_per_unit = abs(entry - initial_stop)
        be_trigger = calculate_be_trigger_price(entry, initial_target, direction)
        mode = trailing_mode if trailing_mode is not None else self.trailing_mode

        pos = PositionState(
            position_id=position_id,
            symbol=symbol,
            direction=direction,
            entry=entry,
            initial_stop=initial_stop,
            initial_target=initial_target,
            initial_atr=initial_atr,
            initial_risk_per_unit=risk_per_unit,
            partial_done=False,
            current_stop=initial_stop,
            be_activated=False,
            be_trigger_price=be_trigger,
            last_applied_stop=initial_stop,
            trailing_mode=mode,
            opened_time=opened_time,
        )
        pos.logs.append(
            f"[POSITION_MGMT] ticket={position_id} dir={'BUY' if direction == PositionDirection.BUY else 'SELL'} "
            f"entry={entry:.5f} current={entry:.5f} tp={initial_target:.5f}"
        )
        self.positions[position_id] = pos
        return pos

    def on_tick(
        self,
        position_id: int,
        current_price: float,
        sym_info: SymbolInfo,
    ) -> Tuple[PositionState, List[str]]:
        """Process a price tick for an open position and update position management state."""
        logs = []
        if position_id not in self.positions:
            logs.append(f"[TRAIL_BLOCKED] reason=MISSING_POSITION ticket={position_id}")
            return None, logs

        pos = self.positions[position_id]
        if pos.is_closed:
            return pos, logs

        dir_sign = 1 if pos.direction == PositionDirection.BUY else -1
        digits = sym_info.digits
        point = sym_info.point
        stops_level_dist = sym_info.stops_level * point

        # 1. Check Exit Conditions (SL / TP hit)
        if pos.direction == PositionDirection.BUY:
            if current_price <= pos.current_stop:
                pos.is_closed = True
                pos.close_reason = "STOP_LOSS"
                log_msg = f"[POSITION_EXIT] ticket={pos.position_id} reason=STOP_LOSS price={current_price:.{digits}f} sl={pos.current_stop:.{digits}f}"
                pos.logs.append(log_msg)
                logs.append(log_msg)
                return pos, logs
            elif pos.initial_target > 0 and current_price >= pos.initial_target:
                pos.is_closed = True
                pos.close_reason = "TAKE_PROFIT"
                log_msg = f"[POSITION_EXIT] ticket={pos.position_id} reason=TAKE_PROFIT price={current_price:.{digits}f} tp={pos.initial_target:.{digits}f}"
                pos.logs.append(log_msg)
                logs.append(log_msg)
                return pos, logs
        else:
            if current_price >= pos.current_stop:
                pos.is_closed = True
                pos.close_reason = "STOP_LOSS"
                log_msg = f"[POSITION_EXIT] ticket={pos.position_id} reason=STOP_LOSS price={current_price:.{digits}f} sl={pos.current_stop:.{digits}f}"
                pos.logs.append(log_msg)
                logs.append(log_msg)
                return pos, logs
            elif pos.initial_target > 0 and current_price <= pos.initial_target:
                pos.is_closed = True
                pos.close_reason = "TAKE_PROFIT"
                log_msg = f"[POSITION_EXIT] ticket={pos.position_id} reason=TAKE_PROFIT price={current_price:.{digits}f} tp={pos.initial_target:.{digits}f}"
                pos.logs.append(log_msg)
                logs.append(log_msg)
                return pos, logs

        # Check for invalid/missing TP
        if pos.initial_target <= 0 or abs(pos.initial_target - pos.entry) <= 0:
            log_msg = f"[TRAIL_BLOCKED] reason=INVALID_TP ticket={pos.position_id}"
            pos.logs.append(log_msg)
            logs.append(log_msg)
            return pos, logs

        if pos.trailing_mode == TrailingMode.OFF:
            return pos, logs

        # Calculate progress towards 50% BE trigger
        tp_distance = abs(pos.initial_target - pos.entry)
        if dir_sign == 1:
            current_progress_dist = current_price - pos.entry
        else:
            current_progress_dist = pos.entry - current_price

        progress_pct = (current_progress_dist / tp_distance) * 100.0 if tp_distance > 0 else 0.0

        # 2. Break-Even Check
        if not pos.be_activated:
            be_reached = (
                (pos.direction == PositionDirection.BUY and current_price >= pos.be_trigger_price) or
                (pos.direction == PositionDirection.SELL and current_price <= pos.be_trigger_price)
            )

            log_be_check = f"[BE_CHECK] progress={progress_pct:.1f}% trigger=50% status={'REACHED' if be_reached else 'PENDING'}"
            pos.logs.append(log_be_check)
            logs.append(log_be_check)

            if be_reached:
                proposed_be_sl = round(pos.entry, digits)
                # Verify stops_level constraint
                if pos.direction == PositionDirection.BUY:
                    valid_stop_dist = (current_price - proposed_be_sl) >= stops_level_dist
                else:
                    valid_stop_dist = (proposed_be_sl - current_price) >= stops_level_dist

                if not valid_stop_dist:
                    log_msg = f"[TRAIL_BLOCKED] reason=STOPS_LEVEL proposed_be={proposed_be_sl:.{digits}f} current={current_price:.{digits}f} min_dist={stops_level_dist:.{digits}f}"
                    pos.logs.append(log_msg)
                    logs.append(log_msg)
                else:
                    # Apply Break-Even
                    pos.be_activated = True
                    log_msg = f"[BE_ACTIVATED] ticket={pos.position_id} entry={pos.entry:.{digits}f} sl={proposed_be_sl:.{digits}f}"
                    pos.logs.append(log_msg)
                    logs.append(log_msg)

                    # Update stop if it improves current stop
                    if (pos.direction == PositionDirection.BUY and proposed_be_sl > pos.current_stop) or \
                       (pos.direction == PositionDirection.SELL and proposed_be_sl < pos.current_stop):
                        old_sl = pos.current_stop
                        pos.current_stop = proposed_be_sl
                        pos.last_applied_stop = proposed_be_sl
                        log_upd = f"[TRAIL_UPDATE] ticket={pos.position_id} old_sl={old_sl:.{digits}f} new_sl={proposed_be_sl:.{digits}f}"
                        pos.logs.append(log_upd)
                        logs.append(log_upd)

        # 3. Dynamic 25% Trailing Stop Logic (Activated after BE)
        if pos.be_activated and pos.trailing_mode == TrailingMode.DYNAMIC_25_PERCENT:
            raw_proposed_sl = calculate_25pct_trailing_sl(pos.entry, current_price, pos.direction)
            proposed_sl = round(raw_proposed_sl, digits)

            log_trail_check = f"[TRAIL_CHECK] progress={progress_pct:.1f}% trail_pct=25% proposed_sl={proposed_sl:.{digits}f} current_sl={pos.current_stop:.{digits}f}"
            pos.logs.append(log_trail_check)
            logs.append(log_trail_check)

            # Mandatory Ratchet Protection Rule
            is_improvement = (
                (pos.direction == PositionDirection.BUY and proposed_sl > pos.current_stop) or
                (pos.direction == PositionDirection.SELL and proposed_sl < pos.current_stop)
            )

            if not is_improvement:
                log_msg = f"[TRAIL_HOLD] proposed_sl={proposed_sl:.{digits}f} existing_sl={pos.current_stop:.{digits}f} reason=NO_IMPROVEMENT"
                pos.logs.append(log_msg)
                logs.append(log_msg)
            else:
                # Broker stops level check
                if pos.direction == PositionDirection.BUY:
                    stops_ok = (current_price - proposed_sl) >= stops_level_dist
                else:
                    stops_ok = (proposed_sl - current_price) >= stops_level_dist

                if not stops_ok:
                    log_msg = f"[TRAIL_BLOCKED] reason=STOPS_LEVEL proposed_sl={proposed_sl:.{digits}f} current={current_price:.{digits}f}"
                    pos.logs.append(log_msg)
                    logs.append(log_msg)
                else:
                    old_sl = pos.current_stop
                    pos.current_stop = proposed_sl
                    pos.last_applied_stop = proposed_sl
                    log_msg = f"[TRAIL_UPDATE] ticket={pos.position_id} old_sl={old_sl:.{digits}f} new_sl={proposed_sl:.{digits}f}"
                    pos.logs.append(log_msg)
                    logs.append(log_msg)

        return pos, logs
