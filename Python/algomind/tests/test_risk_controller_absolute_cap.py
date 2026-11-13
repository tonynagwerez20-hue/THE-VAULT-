
import unittest
from math import isfinite

# Minimal simulation of RiskController logic
def risk_controller_evaluate(equity, risk_pct, max_distortion, min_lot_loss):
    # Base risk budget
    risk_budget = equity * (risk_pct / 100.0)

    # Distortion
    distortion = min_lot_loss / risk_budget if risk_budget > 0 else 999.0

    # Policy cap (ABSOLUTE_MAX_RISK_PERCENT = 2.0)
    absolute_max_risk_pct = 2.0

    # Is the distortion acceptable?
    if distortion > max_distortion:
        return False, "MIN_LOT_UNSAFE"

    # Is the absolute risk acceptable?
    if (min_lot_loss / equity * 100.0) > absolute_max_risk_pct:
        return False, "ESTIMATED_STOP_RISK_ABOVE_2PCT"

    return True, "RISK_OK"

class TestRiskController(unittest.TestCase):
    def test_2pct_cap_enforcement(self):
        # Equity $1000, Risk Percent 0.5% (Budget $5), Max Distortion 5.0
        # If min_lot_loss is $10 (1% of equity), Distortion is $10/$5 = 2.0
        # 2.0 <= 5.0, so distortion is allowed.
        # But 1% <= 2% absolute cap, so this should pass.

        # If min_lot_loss is $25 (2.5% of equity), Distortion is $25/$5 = 5.0
        # 5.0 <= 5.0, so distortion is allowed.
        # But 2.5% > 2% absolute cap, so this should fail!

        equity = 1000.0
        risk_pct = 0.5
        max_distortion = 5.0

        # Test 1: $10 loss (1% of equity)
        allowed, reason = risk_controller_evaluate(equity, risk_pct, max_distortion, 10.0)
        self.assertTrue(allowed, f"Expected allowed, got {reason}")

        # Test 2: $25 loss (2.5% of equity)
        allowed, reason = risk_controller_evaluate(equity, risk_pct, max_distortion, 25.0)
        self.assertFalse(allowed, f"Expected unsafe, got {reason}")
        self.assertEqual(reason, "ESTIMATED_STOP_RISK_ABOVE_2PCT")

if __name__ == "__main__":
    unittest.main()
