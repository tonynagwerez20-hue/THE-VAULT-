"""Offline failure-path tests for external-context artifact publication."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PY_ROOT))

from algomind.bridge.local_bridge import _atomic_write  # noqa: E402


class LocalBridgePublicationCandidate(unittest.TestCase):
    def test_fsync_failure_preserves_previous_complete_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "external.ctx"
            destination.write_text("old=complete\n", encoding="utf-8")
            with patch("algomind.bridge.local_bridge.os.fsync", side_effect=OSError("flush failed")):
                with self.assertRaisesRegex(OSError, "flush failed"):
                    _atomic_write(str(destination), "new=complete\n")
            self.assertEqual(destination.read_text(encoding="utf-8"), "old=complete\n")
            self.assertEqual(list(Path(directory).glob(".amigo-publish-*.tmp")), [])

    def test_replace_failure_preserves_previous_complete_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "external.ctx"
            destination.write_text("old=complete\n", encoding="utf-8")
            with patch("algomind.bridge.local_bridge.os.replace", side_effect=OSError("replace failed")), \
                 patch("algomind.bridge.local_bridge.time.sleep"):
                with self.assertRaisesRegex(OSError, "AMIGO publication failed"):
                    _atomic_write(str(destination), "new=complete\n")
            self.assertEqual(destination.read_text(encoding="utf-8"), "old=complete\n")
            self.assertEqual(list(Path(directory).glob(".amigo-publish-*.tmp")), [])

    def test_successful_replace_publishes_complete_new_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "external.ctx"
            destination.write_text("old=complete\n", encoding="utf-8")
            _atomic_write(str(destination), "new=complete\n")
            self.assertEqual(destination.read_text(encoding="utf-8"), "new=complete\n")
            self.assertEqual(list(Path(directory).glob(".amigo-publish-*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
