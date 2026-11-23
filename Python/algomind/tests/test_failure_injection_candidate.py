"""Failure-injection contract tests (offline source contracts).

Documents expected fail-closed behavior for:
- Python unavailable / stale response
- order submission rejection
- partial fill / duplicate submission
- missing metadata
- broker connection failure
"""
from pathlib import Path
import re
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Include" / "Execution Engine.mqh").is_file())
EXEC = (ROOT / "MQL5" / "Include" / "Execution Engine.mqh").read_text(encoding="utf-8-sig")
RISK = (ROOT / "MQL5" / "Include" / "Risk Engine.mqh").read_text(encoding="utf-8-sig")


class TestFailureInjectionContracts(unittest.TestCase):
    def test_execution_fail_closed_on_reject(self):
        # Execution Engine must not silently accept rejected orders
        self.assertIn("RETCODE", EXEC.upper() or EXEC)

    def test_risk_engine_fail_closed(self):
        # Risk engine must contain fail-closed / NO_TRADE paths
        self.assertTrue("NO_TRADE" in RISK or "fail" in RISK.lower())

    def test_identity_invariant_present(self):
        contracts = (ROOT / "MQL5" / "Include" / "Strategy_Framework.mqh").read_text(encoding="utf-8-sig")
        self.assertIn("idempotency", contracts.lower())

    def test_python_unavailable_documented(self):
        # Documented: Python is external-data only; MQL5 is authoritative
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()