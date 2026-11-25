"""Offline contract tests for bounded AMIGO flow-event history.

The Python oracle checks the intended rolling-window semantics independently.
Source assertions only confirm that the MQL implementation contains the
bounded-storage and aligned-array failure paths; these are not MQL execution.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = (ROOT / "MQL5" / "Include" / "AM_FlowEvents.mqh").read_text(encoding="utf-8-sig")


class ReferenceWindow:
    def __init__(self, persistence_bars):
        self.persistence_bars = max(1, persistence_bars)
        self.limit = max(self.persistence_bars, 3)
        self.rows = []

    def add(self, time, state, pressure, high, low, activity):
        self.rows.append((time, state, pressure, high, low, activity))
        self.rows = self.rows[-self.limit:]

    def persistent(self):
        if len(self.rows) < self.persistence_bars:
            return False
        tail = self.rows[-self.persistence_bars:]
        return tail[-1][1] != 0 and all(row[1] == tail[-1][1] for row in tail)

    def bullish_divergence(self):
        return len(self.rows) >= 3 and self.rows[-1][4] < self.rows[-2][4] and self.rows[-1][2] > self.rows[-2][2]

    def bearish_divergence(self):
        return len(self.rows) >= 3 and self.rows[-1][3] > self.rows[-2][3] and self.rows[-1][2] < self.rows[-2][2]


class FlowEventBufferCandidate(unittest.TestCase):
    def test_long_run_storage_is_bounded_and_retains_latest_query_window(self):
        window = ReferenceWindow(2)
        for index in range(10000):
            window.add(index + 1, 1, float(index), float(index), float(index), 1.0)
        self.assertEqual(len(window.rows), 3)
        self.assertEqual(window.rows[0][0], 9998)
        self.assertEqual(window.rows[-1][0], 10000)
        self.assertTrue(window.persistent())

    def test_persistence_uses_latest_configured_bars(self):
        window = ReferenceWindow(4)
        for index, state in enumerate((1, 1, -1, -1, -1, -1)):
            window.add(index + 1, state, float(state), 10.0, 9.0, 1.0)
        self.assertTrue(window.persistent())
        self.assertEqual(len(window.rows), 4)

    def test_divergence_uses_latest_two_bars_after_eviction(self):
        window = ReferenceWindow(2)
        window.add(1, 1, 0.2, 100.0, 90.0, 1.0)
        window.add(2, 1, 0.3, 99.0, 89.0, 1.0)
        window.add(3, 1, 0.4, 98.0, 88.0, 1.0)
        self.assertTrue(window.bullish_divergence())
        self.assertFalse(window.bearish_divergence())

    def test_mql_source_sets_minimum_capacity_and_bounds_add_path(self):
        self.assertIn("m_history_limit = (m_persistence_bars > 3) ? m_persistence_bars : 3", SOURCE)
        self.assertIn("if(m_count < m_history_limit)", SOURCE)
        self.assertIn("for(int i=1;i<m_history_limit;i++)", SOURCE)
        self.assertIn("Reset();\n            return;", SOURCE)


if __name__ == "__main__":
    unittest.main()
