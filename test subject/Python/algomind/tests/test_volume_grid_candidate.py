"""Offline broker-volume grid tests; these do not execute MQL5."""
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Include").is_dir())
ACCOUNT = (ROOT / "MQL5" / "Include" / "Account Execution Engine.mqh").read_text(encoding="utf-8-sig")


def floor_to_step(requested, step):
    requested = Decimal(str(requested))
    step = Decimal(str(step))
    if requested <= 0 or step <= 0:
        return Decimal("0")
    return (requested / step).to_integral_value(rounding=ROUND_FLOOR) * step


def ceil_to_step(minimum, step):
    minimum = Decimal(str(minimum))
    step = Decimal(str(step))
    if minimum <= 0 or step <= 0:
        return Decimal("0")
    return (minimum / step).to_integral_value(rounding=ROUND_CEILING) * step


def executable_volume(raw, minimum, maximum, step):
    minimum, maximum, step = map(Decimal, map(str, (minimum, maximum, step)))
    if minimum <= 0 or maximum < minimum or step <= 0:
        return Decimal("0")
    minimum_valid = ceil_to_step(minimum, step)
    maximum_valid = floor_to_step(maximum, step)
    if maximum_valid < minimum_valid:
        return Decimal("0")
    volume = floor_to_step(raw, step)
    if volume > maximum:
        volume = floor_to_step(maximum, step)
    if volume < minimum_valid:
        return Decimal("0")
    return volume


class VolumeGridCandidate(unittest.TestCase):
    def test_non_step_aligned_max_is_capped_down(self):
        # The broker permits .03 increments, min=.03 and max=.10. A .12 raw
        # request must cap at .09; sending .10 would violate the step rule.
        volume = executable_volume("0.12", "0.03", "0.10", "0.03")
        self.assertEqual(volume, Decimal("0.09"))
        self.assertLessEqual(volume, Decimal("0.10"))
        self.assertEqual(volume % Decimal("0.03"), Decimal("0"))

    def test_raw_volume_is_floored_and_never_raised_to_minimum(self):
        self.assertEqual(executable_volume("0.029", "0.01", "1.00", "0.01"), Decimal("0.02"))
        self.assertEqual(executable_volume("0.009", "0.01", "1.00", "0.01"), Decimal("0"))

    def test_invalid_grid_or_no_valid_volume_fails_closed(self):
        self.assertEqual(executable_volume("0.05", "0.04", "0.10", "0.03"), Decimal("0"))
        self.assertEqual(executable_volume("0.10", "0.11", "0.10", "0.05"), Decimal("0"))
        self.assertEqual(floor_to_step("0.10", "0"), Decimal("0"))

    def test_non_aligned_metadata_minimum_uses_first_legal_step_without_rounding_raw_up(self):
        self.assertEqual(ceil_to_step("0.01", "0.03"), Decimal("0.03"))
        self.assertEqual(executable_volume("0.04", "0.01", "0.10", "0.03"), Decimal("0.03"))
        self.assertEqual(executable_volume("0.02", "0.01", "0.10", "0.03"), Decimal("0"))
        self.assertEqual(executable_volume("0.10", "0.01", "0.10", "0.03"), Decimal("0.09"))
        # Minimum-lot feasibility must use the actual first legal lot, not the
        # lower-bound metadata value (.03 * $100 = $3, not .01 * $100 = $1).
        self.assertEqual(ceil_to_step("0.01", "0.03") * Decimal("100"), Decimal("3.00"))

    def test_mql_source_floors_both_request_and_cap_and_rejects_empty_grid(self):
        self.assertIn("double AccountVolumeFloorToStep(", ACCOUNT)
        self.assertIn("AccountVolumeFloorToStep(env.raw_volume,env.symbol_cap.volume_step)", ACCOUNT)
        self.assertIn("AccountVolumeFloorToStep(env.symbol_cap.volume_max", ACCOUNT)
        self.assertIn('"INVALID_VOLUME_STEP_GRID"', ACCOUNT)
        self.assertIn("AccountVolumeCeilToStep(cap.volume_min,cap.volume_step)", ACCOUNT)
        self.assertIn("cap.volume_min_valid=min_step_volume", ACCOUNT)
        self.assertIn("env.raw_volume >= env.symbol_cap.volume_min_valid", ACCOUNT)
        self.assertIn("env.symbol_cap.volume_min_valid * env.risk_per_lot", ACCOUNT)

    def test_stop_risk_uses_loss_tick_value_or_adverse_profit_calculation(self):
        self.assertIn("AccountSymbolLossTickValue(symbol)", ACCOUNT)
        helper = ACCOUNT.split("double AccountSymbolLossTickValue(", 1)[1].split("//+------------------------------------------------------------------+", 1)[0]
        self.assertIn("SYMBOL_TRADE_TICK_VALUE_LOSS", helper)
        self.assertIn("ask-tick_size", helper)
        self.assertIn("bid+tick_size", helper)
        self.assertIn("MathMax(worst_loss,-profit)", helper)
        self.assertIn("SRC_MT5_LOSS_DIRECT", ACCOUNT)
        self.assertIn('"NO_VALID_VOLUME_WITHIN_BROKER_LIMITS"', ACCOUNT)
        self.assertNotIn("env.executable_volume = env.symbol_cap.volume_max", ACCOUNT)
        self.assertNotIn("if(env.executable_volume < env.symbol_cap.volume_min) env.executable_volume =", ACCOUNT)


if __name__ == "__main__":
    unittest.main()
