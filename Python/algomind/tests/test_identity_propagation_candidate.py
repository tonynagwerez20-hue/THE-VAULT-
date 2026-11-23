"""Offline source-contract test: P0 identity invariant in Execution Engine."""
from pathlib import Path
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Include" / "Execution Engine.mqh").is_file())
EXEC = (ROOT / "MQL5" / "Include" / "Execution Engine.mqh").read_text(encoding="utf-8-sig")


class TestIdentityPropagation(unittest.TestCase):
    def test_intent_identity_check_present(self):
        self.assertIn("INVALID_INTENT_IDENTITY", EXEC)

    def test_snapshot_id_equals_intent_id(self):
        self.assertIn("ti.snapshot_id!=ti.intent_id", EXEC)


if __name__ == "__main__":
    unittest.main()
