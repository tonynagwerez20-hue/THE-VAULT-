"""Independent offline expectations for safe broker-step partial-close sizing."""
import math
from pathlib import Path
import unittest
from decimal import Decimal, ROUND_FLOOR


ROOT = Path(__file__).resolve().parents[3]
SOURCE = (ROOT / "MQL5" / "Include" / "Position Manager.mqh").read_text(encoding="utf-8-sig")


def expected_close_volume(requested, minimum, step, maximum):
    if (not all(math.isfinite(value) for value in (requested, minimum, step, maximum))
            or requested <= 0 or minimum <= 0 or step <= 0 or maximum < minimum):
        return 0.0
    epsilon = step * 1e-9
    actual = math.floor((requested + epsilon) / step) * step
    actual = min(actual, math.floor((maximum + epsilon) / step) * step)
    return actual if minimum <= actual <= requested + epsilon else 0.0


class PartialCloseVolumeCandidate(unittest.TestCase):
    def test_partial_and_remainder_must_both_be_broker_tradable(self):
        def reduce(volume, fraction, minimum, step, maximum):
            volume, fraction, minimum, step, maximum = map(
                Decimal, (volume, fraction, minimum, step, maximum))
            part = (volume * fraction / step).to_integral_value(rounding=ROUND_FLOOR) * step
            remaining = volume - part
            legal = lambda v: minimum <= v <= maximum and v % step == 0
            return remaining if 0 < part < volume and legal(part) and legal(remaining) else volume

        self.assertEqual(reduce('0.01', '0.5', '0.01', '0.01', '100'), Decimal('0.01'))
        self.assertEqual(reduce('0.03', '0.5', '0.01', '0.01', '100'), Decimal('0.02'))
        self.assertEqual(reduce('0.04', '0.5', '0.03', '0.01', '100'), Decimal('0.04'))
        self.assertEqual(reduce('0.05', '0.5', '0.01', '0.03', '100'), Decimal('0.05'))
        partial = SOURCE.split('if(hit)', 1)[1].split('//--- Invalid TP check guard', 1)[0]
        self.assertEqual(partial.count('ExecutionVolumeValid(sym,part,partial_volume_reason)'), 2)
        self.assertEqual(partial.count('ExecutionVolumeValid(sym,vol-part,partial_volume_reason)'), 2)
        self.assertNotIn('current_volume *=', partial)
        self.assertIn('g_positions[i].current_volume = vol-part;', partial)

    def test_non_step_quantity_rounds_down_not_nearest(self):
        actual = expected_close_volume(0.015, 0.01, 0.01, 100.0)
        self.assertAlmostEqual(actual, 0.01)
        self.assertLessEqual(actual, 0.015)

    def test_subminimum_requested_fraction_is_skipped(self):
        self.assertEqual(expected_close_volume(0.005, 0.01, 0.01, 100.0), 0.0)

    def test_upper_limit_rounding_only_reduces_requested_quantity(self):
        actual = expected_close_volume(2.01, 0.01, 0.01, 2.0)
        self.assertAlmostEqual(actual, 2.0)
        self.assertLessEqual(actual, 2.01)

    def test_invalid_volume_metadata_fails_closed(self):
        for values in ((float("nan"), 0.01, 0.01, 1.0),
                       (0.1, 0.01, 0.0, 1.0),
                       (0.1, 0.0, 0.01, 1.0),
                       (0.1, 0.01, 0.01, 0.005)):
            with self.subTest(values=values):
                self.assertEqual(expected_close_volume(*values), 0.0)

    def test_mql_helper_rounds_down_without_minimum_clamp(self):
        helper = SOURCE.split("double RoundVolume(", 1)[1].split("//+------------------------------------------------------------------+", 1)[0]
        self.assertIn("MathFloor((raw+rounding_epsilon)/step)", helper)
        self.assertNotIn("MathRound", helper)
        self.assertNotIn("rounded = vmin", helper)
        self.assertIn("return 0.0;", helper)


if __name__ == "__main__":
    unittest.main()
