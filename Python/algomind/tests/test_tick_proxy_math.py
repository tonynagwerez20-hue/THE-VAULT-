"""Hardened independent diagnostic oracle and contract tests for compact tick-proxy mathematics.

Covers:
- Strict rejection of NaN, infinity, and intermediate sum overflow.
- Array bounds enforcement (count <= len(deltas) and count <= MAX_BATCH_SIZE).
- Explicit per-metric availability flags for elapsed_seconds and prior_atr.
- Partial and exact quality contracts (INVALID, EMPTY, FLAT, VALID).
- Durable regression coverage for empty inputs, capacity limits, sawtooth paths,
  normalization underflow/overflow, and mathematical coupling identities.
"""
import math
import unittest

MAX_BATCH_SIZE = 100000


def calculate_tick_proxy_metrics(deltas, count=None, elapsed_seconds=60.0, prior_atr=1.0):
    """Hardened reference implementation matching TickProxyMath.mqh contract."""
    if count is None:
        count = len(deltas)

    # 1. Array bounds & count validation
    if not isinstance(count, int) or count < 0:
        return {"quality": "INVALID", "error": "BAD_COUNT"}

    if count == 0:
        return {
            "n": 0, "u": 0, "d": 0, "unchanged": 0,
            "directional_balance": 0.0,
            "moving_fraction": 0.0,
            "normalized_pressure": 0.0,
            "activity_rate": 0.0,
            "activity_rate_available": False,
            "directional_efficiency": 0.0,
            "directional_efficiency_available": False,
            "normalized_displacement": 0.0,
            "normalized_displacement_available": False,
            "quality": "EMPTY"
        }

    if count > len(deltas) or count > MAX_BATCH_SIZE:
        return {"quality": "INVALID", "error": "COUNT_EXCEEDS_CAPACITY"}

    u = 0
    d = 0
    flat = 0
    net_disp = 0.0
    gross_disp = 0.0

    # 2. Iterate elements and validate finite inputs & sum overflow
    for i in range(count):
        delta = deltas[i]
        if not math.isfinite(delta):
            return {"quality": "INVALID", "error": "NON_FINITE_DELTA"}

        if delta > 0.0:
            u += 1
        elif delta < 0.0:
            d += 1
        else:
            flat += 1

        net_disp += delta
        gross_disp += abs(delta)

        if not math.isfinite(net_disp) or not math.isfinite(gross_disp):
            return {"quality": "INVALID", "error": "INTERMEDIATE_OVERFLOW"}

    moving = u + d
    moving_frac = moving / count
    dir_balance = (u - d) / moving if moving > 0 else 0.0
    norm_pressure = (u - d) / count

    # 3. Activity rate contract
    act_rate = 0.0
    act_avail = False
    if elapsed_seconds is not None and math.isfinite(elapsed_seconds) and elapsed_seconds > 0.0:
        rate = count / elapsed_seconds
        if math.isfinite(rate) and rate >= 0.0:
            act_rate = rate
            act_avail = True

    # 4. Directional efficiency contract
    dir_eff = 0.0
    dir_eff_avail = False
    if gross_disp > 0.0:
        eff = abs(net_disp) / gross_disp
        if math.isfinite(eff) and 0.0 <= eff <= 1.00000001:
            dir_eff = min(1.0, eff)
            dir_eff_avail = True

    # 5. Normalized displacement contract
    norm_disp = 0.0
    norm_disp_avail = False
    if prior_atr is not None and math.isfinite(prior_atr) and prior_atr > 0.0:
        disp = net_disp / prior_atr
        if math.isfinite(disp):
            norm_disp = disp
            norm_disp_avail = True

    # 6. Quality label
    quality = "FLAT" if gross_disp == 0.0 else "VALID"

    return {
        "n": count, "u": u, "d": d, "unchanged": flat,
        "directional_balance": dir_balance,
        "moving_fraction": moving_frac,
        "normalized_pressure": norm_pressure,
        "activity_rate": act_rate,
        "activity_rate_available": act_avail,
        "directional_efficiency": dir_eff,
        "directional_efficiency_available": dir_eff_avail,
        "normalized_displacement": norm_disp,
        "normalized_displacement_available": norm_disp_avail,
        "quality": quality
    }


class TestHardenedTickProxyMath(unittest.TestCase):
    def test_rejection_of_nan_and_infinity_deltas(self):
        """NaN or infinite deltas must return INVALID, not propagate into metrics."""
        res_nan = calculate_tick_proxy_metrics([1.0, float("nan"), 1.0])
        self.assertEqual(res_nan["quality"], "INVALID")

        res_inf = calculate_tick_proxy_metrics([1.0, float("inf"), -1.0])
        self.assertEqual(res_inf["quality"], "INVALID")

    def test_rejection_of_sum_overflow(self):
        """Sum overflow (e.g. 1e308 + 1e308) must return INVALID."""
        res_overflow = calculate_tick_proxy_metrics([1e308, 1e308])
        self.assertEqual(res_overflow["quality"], "INVALID")

    def test_array_bounds_rejection(self):
        """Requesting count > len(deltas) must return INVALID."""
        deltas = [1.0, 2.0]
        res_oversized = calculate_tick_proxy_metrics(deltas, count=5)
        self.assertEqual(res_oversized["quality"], "INVALID")

        res_neg = calculate_tick_proxy_metrics(deltas, count=-1)
        self.assertEqual(res_neg["quality"], "INVALID")

    def test_capacity_limit_rejection(self):
        """Count exceeding MAX_BATCH_SIZE (100,000) must return INVALID."""
        res_cap = calculate_tick_proxy_metrics([], count=MAX_BATCH_SIZE + 1)
        self.assertEqual(res_cap["quality"], "INVALID")

    def test_empty_sequence_contract(self):
        """Count 0 returns quality EMPTY and all metric availability flags False."""
        res_empty = calculate_tick_proxy_metrics([])
        self.assertEqual(res_empty["quality"], "EMPTY")
        self.assertEqual(res_empty["n"], 0)
        self.assertFalse(res_empty["activity_rate_available"])
        self.assertFalse(res_empty["directional_efficiency_available"])
        self.assertFalse(res_empty["normalized_displacement_available"])

    def test_invalid_normalization_inputs_flagged_unavailable(self):
        """Invalid elapsed_seconds or prior_atr leaves availability False without spoiling gross displacement."""
        deltas = [1.0, 2.0, -1.0]
        # Invalid elapsed_seconds (<= 0 or non-finite)
        res_bad_time = calculate_tick_proxy_metrics(deltas, elapsed_seconds=0.0)
        self.assertEqual(res_bad_time["quality"], "VALID")
        self.assertFalse(res_bad_time["activity_rate_available"])
        self.assertEqual(res_bad_time["activity_rate"], 0.0)

        # Invalid prior_atr (<= 0 or non-finite)
        res_bad_atr = calculate_tick_proxy_metrics(deltas, prior_atr=-5.0)
        self.assertEqual(res_bad_atr["quality"], "VALID")
        self.assertFalse(res_bad_atr["normalized_displacement_available"])
        self.assertEqual(res_bad_atr["normalized_displacement"], 0.0)

    def test_normalization_overflow_yields_unavailable(self):
        """Tiny positive prior_atr or elapsed time causing float overflow yields unavailable."""
        deltas = [1.0, 1.0]
        res = calculate_tick_proxy_metrics(deltas, elapsed_seconds=1e-320, prior_atr=1e-320)
        self.assertEqual(res["quality"], "VALID")
        # In Python float division by 1e-320 overflows to inf; availability must be False
        self.assertFalse(res["activity_rate_available"])
        self.assertFalse(res["normalized_displacement_available"])

    def test_flat_path_quality_and_metrics(self):
        """Flat sequence gives quality FLAT, directional balance 0, but valid activity rate if duration valid."""
        deltas = [0.0] * 50
        res = calculate_tick_proxy_metrics(deltas, elapsed_seconds=25.0)
        self.assertEqual(res["quality"], "FLAT")
        self.assertEqual(res["directional_balance"], 0.0)
        self.assertEqual(res["moving_fraction"], 0.0)
        self.assertEqual(res["normalized_pressure"], 0.0)
        self.assertFalse(res["directional_efficiency_available"])
        self.assertTrue(res["activity_rate_available"])
        self.assertAlmostEqual(res["activity_rate"], 2.0)

    def test_sawtooth_efficiency_zero(self):
        """Sawtooth +1, -1, +1, -1 yields net 0, gross 4, efficiency 0."""
        deltas = [1.0, -1.0, 1.0, -1.0]
        res = calculate_tick_proxy_metrics(deltas)
        self.assertEqual(res["quality"], "VALID")
        self.assertTrue(res["directional_efficiency_available"])
        self.assertEqual(res["directional_efficiency"], 0.0)
        self.assertEqual(res["directional_balance"], 0.0)

    def test_normalized_displacement_scaling(self):
        """Valid displacement scales exactly with prior valid ATR."""
        deltas = [0.5, 0.5, 1.0]  # net = 2.0
        res = calculate_tick_proxy_metrics(deltas, prior_atr=4.0)
        self.assertEqual(res["quality"], "VALID")
        self.assertTrue(res["normalized_displacement_available"])
        self.assertAlmostEqual(res["normalized_displacement"], 0.5)

    def test_mathematical_identity_coupling(self):
        """normalized_pressure must equal directional_balance * moving_fraction identically."""
        deltas = [1.0] * 30 + [-1.0] * 10 + [0.0] * 60
        res = calculate_tick_proxy_metrics(deltas)
        self.assertEqual(res["quality"], "VALID")
        self.assertAlmostEqual(res["directional_balance"], (30 - 10) / (30 + 10))  # 0.5
        self.assertAlmostEqual(res["moving_fraction"], 40 / 100)  # 0.4
        self.assertAlmostEqual(res["normalized_pressure"], 20 / 100)  # 0.2
        self.assertAlmostEqual(res["normalized_pressure"], res["directional_balance"] * res["moving_fraction"])

    def test_plan_reference_cases_preserved(self):
        """Preserve 100 transitions (1 up, 99 flat) and (100 up)."""
        ex1 = calculate_tick_proxy_metrics([1.0] + [0.0] * 99)
        self.assertEqual(ex1["quality"], "VALID")
        self.assertAlmostEqual(ex1["directional_balance"], 1.0)
        self.assertAlmostEqual(ex1["moving_fraction"], 0.01)
        self.assertAlmostEqual(ex1["normalized_pressure"], 0.01)

        ex2 = calculate_tick_proxy_metrics([1.0] * 100)
        self.assertEqual(ex2["quality"], "VALID")
        self.assertAlmostEqual(ex2["directional_balance"], 1.0)
        self.assertAlmostEqual(ex2["moving_fraction"], 1.0)
        self.assertAlmostEqual(ex2["normalized_pressure"], 1.0)
        self.assertAlmostEqual(ex2["directional_efficiency"], 1.0)


if __name__ == "__main__":
    unittest.main()
