"""Approved horizon selector - hierarchical independent per-horizon evaluation.

Implements the independent Python reference selector for MQL5's
SelectApprovedHorizon function. Evaluates Swing → Intraday → Scalp
horizons with per-horizon TF groups and explicit direction.

This provides Python parity for horizon selection logic and shared
test vectors between MQL5 and Python implementations.
"""

from typing import Literal
from enum import IntEnum

# Horizon enum matching MQL5
class Horizon(IntEnum):
    SWING = 0
    INTRADAY = 1
    SCALPING = 2

# Hypothesis enum matching MQL5
class Hypothesis(IntEnum):
    CONTINUATION = 0
    MEAN_REVERSION = 1

# Regime enum matching MQL5
class Regime(IntEnum):
    BALANCED = 0
    NO_TRADE = 1

# Direction: 1 = buy, -1 = sell, 0 = neutral (should never pass to selector)
Direction = Literal[1, -1]

# TopDownContext structure - directional bias of each TF
class TopDownContext:
    def __init__(self, d1_dir: int, h4_dir: int, h1_dir: int,
                 m30_dir: int, m15_dir: int, m5_dir: int, m1_dir: int,
                 complete: bool, asof_boundary: int, boundary: int):
        self.d1_dir = d1_dir
        self.h4_dir = h4_dir
        self.h1_dir = h1_dir
        self.m30_dir = m30_dir
        self.m15_dir = m15_dir
        self.m5_dir = m5_dir
        self.m1_dir = m1_dir
        self.complete = complete
        self.asof_boundary = asof_boundary
        self.boundary = boundary

# DecisionResult structure - contains decision action, direction, hypothesis
class DecisionResult:
    def __init__(self, action: int, direction: Direction, hypothesis: Hypothesis):
        self.action = action  # ACTION_TRADE or other
        self.direction = direction  # 1 or -1, explicit direction
        self.hypothesis = hypothesis  # CONTINUATION or MEAN_REVERSION

# Constants matching MQL5
ACTION_TRADE = 1
HORIZON_SWING = Horizon.SWING
HORIZON_INTRADAY = Horizon.INTRADAY
HORIZON_SCALPING = Horizon.SCALPING
HYP_CONTINUATION = Hypothesis.CONTINUATION
HYP_MEAN_REVERSION = Hypothesis.MEAN_REVERSION
REGIME_BALANCED = Regime.BALANCED
REGIME_NO_TRADE = Regime.NO_TRADE


def select_approved_horizon(td: TopDownContext, decision: DecisionResult,
                          regime: Regime, boundary: int) -> Horizon:
    """Hierarchical horizon selection: independent evaluation per horizon.

    Evaluates Swing → Intraday → Scalp horizons with per-horizon TF groups.
    Longer-horizon failure does not suppress shorter valid horizons.
    Missing/invalid TF data = hard reject.

    Args:
        td: TopDownContext with TF directional biases
        decision: DecisionResult with action, direction, hypothesis
        regime: Current trading regime
        boundary: Timestamp boundary for snapshot

    Returns:
        Horizon: Selected horizon (SWING, INTRADAY, or SCALPING)
                 or 0 (invalid) if no horizon approved
    """
    horizon = Horizon(0)  # Default to invalid horizon

    # Safety gates - same as MQL5 implementation
    if not td.complete or boundary <= 0 or td.asof_boundary != boundary:
        return Horizon(0)
    if decision.action != ACTION_TRADE or decision.direction not in (1, -1):
        return Horizon(0)

    # Validate all TFs are in valid range [-1, 1]
    dirs = [td.d1_dir, td.h4_dir, td.h1_dir, td.m30_dir, td.m15_dir, td.m5_dir, td.m1_dir]
    for i in range(7):
        if dirs[i] < -1 or dirs[i] > 1:
            return Horizon(0)

    # Evaluate Swing horizon first (highest priority)
    if evaluate_horizon_for_trend(td, decision.direction, decision.hypothesis,
                                 regime, HORIZON_SWING):
        horizon = HORIZON_SWING
        return horizon

    # Evaluate Intraday horizon (second priority)
    if evaluate_horizon_for_trend(td, decision.direction, decision.hypothesis,
                                 regime, HORIZON_INTRADAY):
        horizon = HORIZON_INTRADAY
        return horizon

    # Evaluate Scalp horizon (lowest priority, allows countertrend)
    if evaluate_horizon_for_trend(td, decision.direction, decision.hypothesis,
                                 regime, HORIZON_SCALPING):
        horizon = HORIZON_SCALPING
        return horizon

    return Horizon(0)


def evaluate_horizon_for_trend(td: TopDownContext, direction: Direction,
                               hypothesis: Hypothesis, regime: Regime,
                               horizon: Horizon) -> bool:
    """Evaluate a specific horizon based on its TF groups and directional bias.

    Args:
        td: TopDownContext with TF directional biases
        direction: Explicit direction from decision (1 or -1)
        hypothesis: CONTINUATION or MEAN_REVERSION hypothesis
        regime: Current trading regime
        horizon: HORIZON_SWING, HORIZON_INTRADAY, or HORIZON_SCALPING

    Returns:
        bool: True if horizon approved, False otherwise
    """
    d = direction  # Use explicit direction from decision
    if d not in (1, -1):  # Invalid direction
        return False

    # Define TF groups for each horizon - exact MQL5 mapping
    if horizon == HORIZON_SWING:
        # Swing: Context (D1,H4), Setup (H1,M30,M15), Entry (M5,M1)
        context_dirs = [td.d1_dir, td.h4_dir]
        setup_dirs = [td.h1_dir, td.m30_dir, td.m15_dir]
        entry_dirs = [td.m5_dir, td.m1_dir]
        context_count = 2
        setup_count = 3
        entry_count = 2

    elif horizon == HORIZON_INTRADAY:
        # Intraday: Context (D1,H4), Setup (H1,M30), Entry (M15,M5)
        context_dirs = [td.d1_dir, td.h4_dir]
        setup_dirs = [td.h1_dir, td.m30_dir]
        entry_dirs = [td.m15_dir, td.m5_dir]
        context_count = 2
        setup_count = 2
        entry_count = 2

    elif horizon == HORIZON_SCALPING:
        # Scalp: Context (H1,M30), Setup (M15,M5), Entry (M1)
        context_dirs = [td.h1_dir, td.m30_dir]
        setup_dirs = [td.m15_dir, td.m5_dir]
        entry_dirs = [td.m1_dir]
        context_count = 2
        setup_count = 2
        entry_count = 1

    else:
        return False  # Invalid horizon

    # Check for missing/invalid TF data (hard reject) - exact MQL5 logic
    for i in range(context_count):
        if context_dirs[i] < -1 or context_dirs[i] > 1:
            return False
    for i in range(setup_count):
        if setup_dirs[i] < -1 or setup_dirs[i] > 1:
            return False
    for i in range(entry_count):
        if entry_dirs[i] < -1 or entry_dirs[i] > 1:
            return False

    # For continuation hypothesis - exact MQL5 logic
    if hypothesis == HYP_CONTINUATION:
        # Use explicit direction from decision (not inferred)

        # Check entry trigger matches direction
        if entry_count == 0 or entry_dirs[0] != d:
            return False

        # Check setup support
        setup_ok = False
        if setup_count >= 2:
            # At least 2 of setup TFs should support direction
            support = 0
            for i in range(setup_count):
                if setup_dirs[i] == d or setup_dirs[i] == 0:
                    support += 1
            setup_ok = (support >= 2)
        elif setup_count == 1:
            setup_ok = (setup_dirs[0] == d or setup_dirs[0] == 0)

        if not setup_ok:
            return False

        # For scalp horizon, allow countertrend (opposing HTF) if setup+entry support direction
        if horizon == HORIZON_SCALPING:
            # Scalp can trade against HTF bias if setup and entry support direction
            return True

        # For swing/intraday, require context support
        if horizon == HORIZON_SWING or horizon == HORIZON_INTRADAY:
            # Context should not strongly oppose
            if context_count >= 2 and context_dirs[0] == -d and context_dirs[1] == -d:
                return False

        return True

    # For mean reversion hypothesis - exact MQL5 logic
    if hypothesis == HYP_MEAN_REVERSION and regime == REGIME_BALANCED:
        # MR requires neutral context
        context_neutral = True
        for i in range(context_count):
            if context_dirs[i] != 0:
                context_neutral = False
                break

        # Setup should be neutral or mixed
        setup_neutral = True
        for i in range(setup_count):
            if setup_dirs[i] != 0:
                setup_neutral = False
                break

        # Entry should be neutral
        entry_neutral = True
        for i in range(entry_count):
            if entry_dirs[i] != 0:
                entry_neutral = False
                break

        if context_neutral and setup_neutral and entry_neutral:
            return True

    return False


def tf_bias(dirs: list, confidences: list = None, weights: list = None) -> float:
    """Calculate weighted directional bias (TFBias helper).

    Formula: B_d = SUM(w_i * c_i * d_i) / SUM(w_i * c_i)

    Args:
        dirs: List of directional bias values (+1, 0, -1)
        confidences: Normalized confidence values (default 1.0)
        weights: Timeframe weights (default 1.0)

    Returns:
        float: Weighted directional bias between -1 and +1
    """
    if confidences is None:
        confidences = [1.0] * len(dirs)
    if weights is None:
        weights = [1.0] * len(dirs)

    # Validate input lengths
    if not (len(dirs) == len(confidences) == len(weights)):
        raise ValueError("dirs, confidences, and weights must have same length")

    numerator = 0.0
    denominator = 0.0

    for i in range(len(dirs)):
        # Skip neutral directions from denominator (valid_count logic)
        if dirs[i] != 0:
            denominator += weights[i] * confidences[i]

        # Include all directions in numerator (like MQL5 logic)
        numerator += weights[i] * confidences[i] * dirs[i]

    if denominator == 0:
        return 0.0  # No valid TF directions for bias calculation

    return numerator / denominator


# Test helper function to create TopDownContext from TF values
def make_context(d1: int, h4: int, h1: int, m30: int, m15: int, m5: int, m1: int) -> TopDownContext:
    """Helper to create TopDownContext with boolean complete flag and boundary."""
    return TopDownContext(d1, h4, h1, m30, m15, m5, m1, True, 1, 1)


def make_decision(action: int, direction: Direction, hypothesis: Hypothesis) -> DecisionResult:
    """Helper to create DecisionResult."""
    return DecisionResult(action, direction, hypothesis)