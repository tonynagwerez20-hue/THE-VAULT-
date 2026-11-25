"""Offline contract checks for timestamp-bounded stop-geometry history.

Reference-model testing: validates exact snapshot invariants and closed-bar equality.
"""
from pathlib import Path
import unittest

ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "MQL5" / "Experts" / "AMIGO.mq5").is_file()
)
AMIGO = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")


def geometry_snapshot_valid(decision_boundary: int,
                            closed_bar_time: int,
                            geometry_boundary: int,
                            geometry_latest: int,
                            exec_boundary_after: int,
                            exec_latest_after: int) -> bool:
    """Exact production contract:
    - Geometry boundary and latest must precede/equal decision boundary.
    - Geometry latest must be strictly older than geometry boundary.
    - Post-read execution bar state must EXACTLY match the captured opportunity:
      exec_boundary_after == decision_boundary AND exec_latest_after == closed_bar_time.
    """
    if (decision_boundary <= 0 or closed_bar_time <= 0 or
        geometry_boundary <= 0 or geometry_latest <= 0):
        return False

    # Closed-bar invariant on execution timeframe
    if closed_bar_time >= decision_boundary:
        return False

    # Geometry timeframe bounds
    if geometry_latest >= geometry_boundary:
        return False
    if geometry_boundary > decision_boundary or geometry_latest >= decision_boundary:
        return False

    # Strict equality re-check on execution timeframe after CopyRates
    if exec_boundary_after != decision_boundary:
        return False
    if exec_latest_after != closed_bar_time:
        return False

    return True


class TestGeometrySnapshotBoundary(unittest.TestCase):
    def test_source_wiring_contains_exact_equality_checks(self):
        start = AMIGO.index("ENUM_TIMEFRAMES stop_tf = g_cfg.tf_exec;")
        end = AMIGO.index("if(got > 20)", start)
        block = AMIGO[start:end]

        self.assertIn("geometry_boundary>decision_boundary", block)
        self.assertIn("geometry_latest>=decision_boundary", block)
        self.assertIn("iTime(g_symbol,g_cfg.tf_exec,0)!=decision_boundary", block)
        self.assertIn("iTime(g_symbol,g_cfg.tf_exec,1)!=closed_bar_time", block)
        self.assertLess(block.index("CopyRates(g_symbol, stop_tf, 1, 200, r)"),
                        block.index("iTime(g_symbol,g_cfg.tf_exec,0)!=decision_boundary"))

    def test_exact_closed_bar_equality_contract(self):
        # Normal valid case: decision=1000, closed=940 (M1), geometry=900, latest=600 (M5)
        self.assertTrue(geometry_snapshot_valid(1000, 940, 900, 600, 1000, 940))

        # Rejection: execution closed-bar time shifted during read (e.g. 940 -> 939 or 941)
        # Even if still earlier than decision boundary (e.g. 900 < 1000), mismatch must reject!
        self.assertFalse(geometry_snapshot_valid(1000, 940, 900, 600, 1000, 900),
                         "Must reject when exec_latest_after != closed_bar_time")

        # Rejection: execution boundary advanced during read (new bar formed)
        self.assertFalse(geometry_snapshot_valid(1000, 940, 900, 600, 1060, 1000))

        # Rejection: geometry boundary leaked ahead of decision boundary
        self.assertFalse(geometry_snapshot_valid(1000, 940, 1020, 900, 1000, 940))

        # Rejection: geometry latest >= decision boundary (unclosed data leakage)
        self.assertFalse(geometry_snapshot_valid(1000, 940, 1000, 1000, 1000, 940))


if __name__ == "__main__":
    unittest.main()
