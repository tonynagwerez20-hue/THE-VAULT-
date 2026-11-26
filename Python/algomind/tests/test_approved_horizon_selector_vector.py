"""Shared test vectors between MQL5 and Python horizon selector.

Test vectors for hierarchical horizon selector implementation to validate
MQL5/Python parity. Each vector contains inputs and expected outputs that
should match between the MQL5 and Python implementations.

Vector format matches MQL5 SelectApprovedHorizon contract:
- td: TopDownContext with TF directional biases
- decision: DecisionResult with action, direction, hypothesis
- regime: ENUM_REGIME value
- boundary: datetime boundary
- expected_horizon: HORIZON_SWING, HORIZON_INTRADAY, HORIZON_SCALPING, or 0
"""

from algomind.mgle.approved_horizon_selector import (
    TopDownContext, DecisionResult, select_approved_horizon,
    Horizon, Hypothesis, Regime, make_context, make_decision
)

# Test vectors for hierarchy and per-horizon independence
# Each tuple: (td, decision, regime, boundary, expected_horizon)

test_vectors = [
    # === HORIZONTY FAILURE DOES NOT BLOCK SHORTER ===
    # Swing fails but Intraday succeeds (true case: Entry mismatch on M5 vs M15)
    # Setup: Swing entry M5=0 fails, Intraday entry M15=1 passes
    (
        make_context(1, 1, 1, 1, 1, 0, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.INTRADAY  # Swing M5=0 fails entry, Intraday M15=1 passes
    ),
    # Swing fails but Intraday fails -> Scalp succeeds (original case)
    # Setup: All HTFs oppose direction (Swing context support fails)
    #        but Intraday also uses D1,H4 as context so fails too, falls to Scalp
    (
        make_context(-1, -1, 1, 1, 1, 1, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SCALPING  # Falls through to Scalp because Swing/Intraday context oppose (-1, -1)
    ),
    # Intraday fails but Scalp succeeds (countertrend)
    (
        make_context(1, 1, 1, 1, 0, 0, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SCALPING  # Should select Scalp, ignoring HTF bias
    ),

    # === COUNTERTREND SCALPING SUPPORT ===
    # HTF bias is -1 (short), but Scalp can go long when setup+entry support
    (
        make_context(-1, -1, -1, -1, 1, 1, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SCALPING  # Countertrend scalp allowed
    ),
    # HTF bias is +1 (long), Scalp can go short when setup+entry support
    (
        make_context(1, 1, 1, 1, -1, -1, -1),
        make_decision(1, -1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SCALPING  # Countertrend scalp allowed
    ),

    # === LONGEST ELIGIBLE SELECTED ===
    # All higher TFs support (Swing)
    (
        make_context(1, 1, 1, 1, 1, 1, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SWING  # Should pick Swing (longest)
    ),
    # Only HTF support, no setup (Intraday)
    (
        make_context(1, 1, 0, 0, 0, 0, 0),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SWING  # d1 & h4 support, enough for Swing
    ),

    # === MISSING INVALID TF DATA REJECTION ===
    # Invalid TF value outside [-1,1]
    (
        make_context(1, 1, 2, 1, 1, 1, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon(0)  # h1_dir=2 invalid -> reject
    ),

    # === SETUP+ENTRY DIRECTION REQUIREMENTS ===
    # Entry doesn't match direction
    (
        make_context(1, 1, 1, 1, 1, 1, -1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon(0)  # m1_dir opposes direction -> reject
    ),
    # Setup insufficient support (only 1 of 2+ required)
    (
        make_context(1, 1, 1, 0, 0, 1, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon(0)  # Only 1 setup TF supports
    ),

    # === CONTEXT STRONG OPPOSITION REJECTION ===
    # Swing: Both context TFs strongly oppose (d1=-1, h4=-1), entry supports
    (
        make_context(-1, -1, 1, 1, 1, 1, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SCALPING  # Scalp allows countertrend, so it succeeds instead of returning 0
    ),
    # Intraday: Context opposed but Scalp would work (different TF groups)
    # For Scalp to succeed: H1,M30 context support (1,1), M15,M5 setup support (0,1 counts as 2), M1 entry support (1)
    (
        make_context(-1, -1, 1, 1, 0, 1, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SCALPING  # Context D1,H4 are -1, so Swing and Intraday fail; Scalping uses H1,M30 context which are 1 (supportive), M15=0,M5=1 setup (counts as 2 support), M1=1 entry matches → Scalp succeeds
    ),

    # === MEAN REVERSION LOGIC ===
    # All TFs neutral for MR (requires REGIME_BALANCED)
    (
        make_context(0, 0, 0, 0, 0, 0, 0),
        make_decision(1, 1, Hypothesis.MEAN_REVERSION),
        Regime.BALANCED,
        1,
        Horizon.SWING  # Swing comes first and matches neutral TFs
    ),
    # Non-balanced regime for MR -> reject
    (
        make_context(0, 0, 0, 0, 0, 0, 0),
        make_decision(1, 1, Hypothesis.MEAN_REVERSION),
        Regime.NO_TRADE,
        1,
        Horizon(0)  # MR requires REGIME_BALANCED
    ),

    # === ACTION/REGIME SAFETY GATES ===
    # Non-trade action -> reject
    (
        make_context(1, 1, 1, 1, 1, 1, 1),
        make_decision(0, 1, Hypothesis.CONTINUATION),  # Not ACTION_TRADE
        Regime.BALANCED,
        1,
        Horizon(0)  # action != ACTION_TRADE -> reject
    ),

    # === HORIZON-SPECIFIC ENTRY REQUIREMENTS ===
    # Swing: M5 supports direction
    (
        make_context(1, 1, 1, 1, 1, 1, 1),
        make_decision(1, 1, Hypothesis.CONTINUATION),
        Regime.BALANCED,
        1,
        Horizon.SWING  # m5_dir=1 supports direction
    ),
]


def run_test_vector(td: TopDownContext, decision: DecisionResult,
                   regime: Regime, boundary: int, expected: Horizon) -> None:
    """Run a single test vector and validate result.

    Args:
        td: TopDownContext with TF directional biases
        decision: DecisionResult with action, direction, hypothesis
        regime: ENUM_REGIME value
        boundary: datetime boundary
        expected: Expected horizon result

    Raises:
        AssertionError: If actual result doesn't match expected
    """
    result = select_approved_horizon(td, decision, regime, boundary)

    if result != expected:
        print(f"FAILED vector test:")
        print(f"  Inputs: td({[td.d1_dir,td.h4_dir,td.h1_dir,td.m30_dir,td.m15_dir,td.m5_dir,td.m1_dir]}), ")
        print(f"          decision(action={decision.action}, dir={decision.direction}, hyp={decision.hypothesis}), ")
        print(f"          regime={regime}, boundary={boundary}")
        print(f"  Expected: {expected}")
        print(f"  Actual:   {result}")
        raise AssertionError(f"Test vector failed: expected {expected}, got {result}")
    else:
        print(f"✓ PASSED: {result}")


if __name__ == "__main__":
    print(f"Running {len(test_vectors)} shared test vectors...")

    passed = 0
    failed = 0

    for i, (td, decision, regime, boundary, expected) in enumerate(test_vectors):
        print(f"\nTest {i+1}/{len(test_vectors)}:")
        try:
            run_test_vector(td, decision, regime, boundary, expected)
            passed += 1
        except AssertionError as e:
            print(f"  {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"SUMMARY: {passed} passed, {failed} failed")

    if failed == 0:
        print("All tests passed! ✅")
    else:
        print(f"❌ {failed} test(s) failed")
        exit(1)