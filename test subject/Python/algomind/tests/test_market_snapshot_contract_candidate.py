"""Offline tests for the MQL5-to-Python market snapshot boundary."""
from datetime import datetime, timezone
import math
from pathlib import Path
import sys
import tempfile
import unittest
import os
import time
from unittest.mock import patch

PY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PY_ROOT))

from algomind.bridge.local_bridge import read_market_snapshot  # noqa: E402
from algomind.schema import DataQuality, SCHEMA_VERSION  # noqa: E402
import run_external_service as service  # noqa: E402


def snapshot_text(**overrides):
    values = {
        "snapshot_id": 123456,
        "decision_boundary": 600,
        "closed_bar_time": 300,
        "timeframe": 5,
        "max_age_s": 120,
        "timestamp": 1234,
        "symbol": "XAUUSD",
        "bid": 2000.0,
        "ask": 2000.2,
        "spread": 0.2,
        "atr14": 10.0,
        "structure_dir": 1,
        "close": 2000.1,
        "equity": 1000.0,
        "session_state": 0,
        "schema_version": SCHEMA_VERSION,
    }
    values.update(overrides)
    return "".join(f"{key}={value}\n" for key, value in values.items())


def snapshot_core_values_valid(values):
    """Independent numeric oracle for required source snapshot inputs."""
    finite = lambda key: math.isfinite(float(values[key]))
    return (
        values.get("symbol", "") != ""
        and all(finite(key) for key in ("bid", "ask", "spread", "point", "tick_size",
                                       "tick_value", "contract_size", "volume_min",
                                       "volume_max", "volume_step", "equity", "balance",
                                       "margin_free", "stops_level", "freeze_level"))
        and values["bid"] > 0
        and values["ask"] >= values["bid"]
        and values["spread"] >= 0
        and values["point"] > 0
        and values["tick_size"] > 0
        and values["contract_size"] > 0
        and values["volume_min"] > 0
        and values["volume_max"] >= values["volume_min"]
        and values["volume_step"] > 0
        and values["stops_level"] >= 0
        and values["freeze_level"] >= 0
        and values["equity"] > 0
        and values["balance"] >= 0
    )


class MarketSnapshotContractCandidate(unittest.TestCase):
    def setUp(self):
        self.service_state = {
            name: getattr(service, name)
            for name in ("_cached_cftc", "_last_cftc_fetch", "_cached_options",
                         "_last_options_fetch", "_cached_news", "_last_news_fetch")
        }

    def tearDown(self):
        for name, value in self.service_state.items():
            setattr(service, name, value)

    def test_complete_writer_compatible_snapshot_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.snapshot"
            path.write_text(snapshot_text(), encoding="utf-8")
            # Control transport age explicitly so this contract test does not
            # depend on wall-clock scheduling or filesystem timestamp timing.
            captured_mtime = 1_790_000_000.0
            os.utime(path, (captured_mtime, captured_mtime))
            with patch("algomind.bridge.local_bridge.time.time",
                       return_value=captured_mtime + 1.0):
                snapshot = read_market_snapshot(str(path))
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.symbol, "XAUUSD")
        self.assertEqual(snapshot.schema_version, SCHEMA_VERSION)
        self.assertLess(snapshot.closed_bar_time, snapshot.decision_boundary)
        self.assertEqual(snapshot.timeframe, 5)

    def test_missing_required_key_is_rejected_instead_of_default_filled(self):
        text = snapshot_text().replace("close=2000.1\n", "")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.snapshot"
            path.write_text(text, encoding="utf-8")
            self.assertIsNone(read_market_snapshot(str(path)))

    def test_wrong_schema_invalid_quote_and_nonfinite_input_are_rejected(self):
        cases = (
            snapshot_text(schema_version=SCHEMA_VERSION + 1),
            snapshot_text(ask=1999.0),
            snapshot_text(atr14="nan"),
            snapshot_text(closed_bar_time=600),
            snapshot_text(timeframe=0),
            snapshot_text(max_age_s=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.snapshot"
            for text in cases:
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    self.assertIsNone(read_market_snapshot(str(path)))

    def test_snapshot_age_uses_the_limit_frozen_by_mql(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.snapshot"
            path.write_text(snapshot_text(), encoding="utf-8")
            now = time.time()
            for mtime in (now - 121.0, now + 1.0):
                with self.subTest(mtime=mtime):
                    os.utime(path, (mtime, mtime))
                    with patch("algomind.bridge.local_bridge.time.time", return_value=now):
                        self.assertIsNone(read_market_snapshot(str(path)))
            path.write_text(snapshot_text(max_age_s=60), encoding="utf-8")
            for mtime, expected in ((now - 61.0, None), (now - 59.0, 123456)):
                with self.subTest(mtime=mtime, expected=expected):
                    os.utime(path, (mtime, mtime))
                    with patch("algomind.bridge.local_bridge.time.time", return_value=now):
                        snapshot = read_market_snapshot(str(path))
                    self.assertEqual(None if snapshot is None else snapshot.snapshot_id, expected)

    def test_stale_snapshot_disables_options_without_disabling_fresh_news(self):
        now = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.snapshot"
            path.write_text(snapshot_text(), encoding="utf-8")
            os.utime(path, (now.timestamp() - 121.0, now.timestamp() - 121.0))
            service._cached_cftc = None
            service._last_cftc_fetch = 0.0
            service._cached_news = None
            service._last_news_fetch = 0.0
            service._cached_options = {"options_valid": True, "gamma_regime": 1}
            service._last_options_fetch = now.timestamp()
            with patch.object(service, "cftc_ctx", return_value={"cftc_valid": False}), \
                 patch.object(service, "news_ctx", return_value={"news_valid": True,
                                                                   "news_observed_ts": int(now.timestamp()),
                                                                   "news_event_ts": 0,
                                                                   "news_active_window": False}), \
                 patch.object(service, "options_ctx") as options, \
                 patch("algomind.bridge.local_bridge.time.time", return_value=now.timestamp()):
                context = service.build_context(str(path), now)
        options.assert_not_called()
        self.assertFalse(context.options_valid)
        self.assertTrue(context.news_valid)
        self.assertIsNone(service._cached_options)

    def test_mql_writer_requires_matching_opportunity_and_closed_bar_identity(self):
        include = (PY_ROOT.parent / "MQL5" / "Include" / "External Context Compactor.mqh").read_text(
            encoding="utf-8-sig")
        writer = include.split("void WriteSnapshotForExternal(", 1)[1]
        for token in ("s.snapshot_id!=f.snapshot_id", "s.decision_boundary!=f.decision_boundary",
                      "s.closed_bar_time!=f.closed_bar_time", "f.timestamp!=s.closed_bar_time",
                      "f.timeframe!=(int)g_cfg.tf_exec",
                      "s.external_max_age_s<=0", "max_age_s=%d",
                      "decision_boundary=%I64d", "closed_bar_time=%I64d", "timeframe=%d"):
            self.assertIn(token, writer)

    def test_mql_snapshot_builder_rejects_nonfinite_and_invalid_core_inputs(self):
        root = PY_ROOT.parent
        builder = (root / "MQL5" / "Include" / "Market Snapshot Builder.mqh").read_text(
            encoding="utf-8-sig")
        for field in ("bid", "ask", "spread", "point", "tick_size", "tick_value",
                      "contract_size", "volume_min", "volume_max", "volume_step",
                      "equity", "balance", "margin_free"):
            self.assertIn(f"MathIsValidNumber(s.{field})", builder)
        self.assertIn("s.ask<s.bid", builder)
        self.assertIn("s.data_quality |= DQ_BROKER_INVALID | DQ_FATAL", builder)
        self.assertIn("s.data_quality |= DQ_FATAL", builder)

        base = {
            "symbol": "XAUUSD", "bid": 2000.0, "ask": 2000.2, "spread": 0.2,
            "point": 0.01, "tick_size": 0.01, "tick_value": 1.0,
            "contract_size": 100.0, "volume_min": 0.01, "volume_max": 100.0,
            "volume_step": 0.01, "equity": 1000.0, "balance": 1000.0,
            "margin_free": 900.0, "stops_level": 0.0, "freeze_level": 0.0,
        }
        self.assertTrue(snapshot_core_values_valid(base))
        for key, value in (("bid", float("nan")), ("ask", float("inf")),
                           ("equity", float("nan")), ("tick_size", float("inf")),
                           ("volume_step", 0.0), ("ask", 1999.0)):
            with self.subTest(key=key, value=value):
                self.assertFalse(snapshot_core_values_valid({**base, key: value}))

    def test_external_writer_uses_frozen_equity_and_validated_closed_bar_close(self):
        root = PY_ROOT.parent
        writer = (root / "MQL5" / "Include" / "External Context Compactor.mqh").read_text(
            encoding="utf-8-sig").split("void WriteSnapshotForExternal(", 1)[1]
        expert = (root / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")
        contract = (root / "MQL5" / "Include" / "Contracts header.mqh").read_text(encoding="utf-8-sig")
        self.assertIn("double   closed_bar_close;", contract)
        self.assertIn("candidate_snap.closed_bar_close=candidate_feature_rates[0].close;", expert)
        self.assertIn("candidate_snap.external_max_age_s=g_cfg.stale_threshold_s;", expert)
        self.assertIn("#define Amigo_SCHEMA_VERSION 104", contract)
        schema = (PY_ROOT / "algomind" / "schema.py").read_text(encoding="utf-8-sig")
        self.assertIn("SCHEMA_VERSION = 104", schema)
        self.assertIn("s.closed_bar_close", writer)
        self.assertIn("s.equity", writer)
        self.assertNotIn("iClose(s.symbol", writer)
        self.assertNotIn("AccountInfoDouble(ACCOUNT_EQUITY)", writer)

    def test_missing_snapshot_never_calls_options_or_reuses_cached_context(self):
        now = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
        service._cached_cftc = None
        service._last_cftc_fetch = 0.0
        service._cached_news = None
        service._last_news_fetch = 0.0
        service._cached_options = {"options_valid": True, "gamma_regime": 2}
        service._last_options_fetch = now.timestamp()
        with patch.object(service, "cftc_ctx", return_value={"cftc_valid": False}), \
             patch.object(service, "news_ctx", return_value={"news_valid": False}), \
             patch.object(service, "options_ctx") as options:
            context = service.build_context("missing.snapshot", now)
        options.assert_not_called()
        self.assertFalse(context.options_valid)
        self.assertEqual(context.options_source, "NONE")
        self.assertFalse(hasattr(context, "gamma_regime"))
        self.assertTrue(context.data_quality & DataQuality.EXTERNAL_ABSENT)
        self.assertIsNone(service._cached_options)

    def test_valid_snapshot_does_not_authorize_unmapped_options(self):
        now = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.snapshot"
            path.write_text(snapshot_text(), encoding="utf-8")
            fresh_mtime = time.time()
            os.utime(path, (fresh_mtime, fresh_mtime))
            service._cached_cftc = {"cftc_valid": False}
            service._cached_news = {"news_valid": False}
            service._cached_options = None
            with patch.object(service, "options_ctx", return_value={"options_valid": False}) as options:
                service.build_context(str(path), now)
        options.assert_not_called()


if __name__ == "__main__":
    unittest.main()
