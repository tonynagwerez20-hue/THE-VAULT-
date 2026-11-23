"""Offline NEWS availability contract tests; HTTP is fully stubbed."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PY_ROOT))

from algomind.external import news_adapter as news  # noqa: E402
from algomind.schema import ExternalContext, SCHEMA_VERSION  # noqa: E402


class Response:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content


class NewsAvailabilityCandidate(unittest.TestCase):
    def test_empty_weekly_root_is_unavailable_not_confirmed_no_event(self):
        now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        with patch.object(news.requests, "get", return_value=Response(200, b"<weeklyevents/>")):
            result = news.compute_context(now, fetch_completed_at=now)
        self.assertFalse(result["news_valid"])
        self.assertFalse(result["news_active_window"])
        self.assertEqual(result["news_observed_ts"], 0)

    def test_nonempty_calendar_without_relevant_event_is_valid_no_event(self):
        now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        xml = b"""<weeklyevents><event><country>JPY</country><impact>Low</impact>
        <title>Manufacturing PMI</title><date>01-05-2026</date><time>09:30am</time>
        </event></weeklyevents>"""
        with patch.object(news.requests, "get", return_value=Response(200, xml)):
            result = news.compute_context(now, fetch_completed_at=now)
        self.assertTrue(result["news_valid"])
        self.assertFalse(result["news_active_window"])
        self.assertEqual(result["news_observed_ts"], int(now.timestamp()))

    def test_network_http_and_parse_failures_are_unavailable(self):
        now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        failures = [
            news.requests.Timeout("offline"),
        ]
        with patch.object(news.requests, "get", side_effect=failures[0]):
            self.assertIsNone(news.fetch_news_events())
        with patch.object(news.requests, "get", return_value=Response(503, b"")):
            self.assertIsNone(news.fetch_news_events())
        with patch.object(news.requests, "get", return_value=Response(200, b"<broken")):
            result = news.compute_context(now, fetch_completed_at=now)
        self.assertFalse(result["news_valid"])
        self.assertEqual(result["news_observed_ts"], 0)

    def test_http_200_with_wrong_xml_root_is_unavailable(self):
        # A parseable upstream/proxy error document is not a quiet calendar.
        with patch.object(news.requests, "get", return_value=Response(200, b"<error><message>upstream unavailable</message></error>")):
            self.assertIsNone(news.fetch_news_events())

    def test_active_event_is_valid_and_carries_separate_observation_time(self):
        now = datetime(2026, 1, 5, 14, 15, tzinfo=timezone.utc)
        xml = b"""<weeklyevents><event><country>USD</country><impact>High</impact>
        <title>CPI</title><date>01-05-2026</date><time>09:30am</time>
        <forecast>2.0</forecast><actual></actual></event></weeklyevents>"""
        with patch.object(news.requests, "get", return_value=Response(200, xml)):
            result = news.compute_context(now, fetch_completed_at=now)
        self.assertTrue(result["news_valid"])
        self.assertTrue(result["news_active_window"])
        self.assertNotEqual(result["news_event_ts"], result["news_observed_ts"])
        self.assertEqual(result["news_observed_ts"], int(now.timestamp()))

    def test_published_actual_value_is_used_after_scheduled_time(self):
        now = datetime(2026, 1, 5, 14, 35, tzinfo=timezone.utc)
        xml = b"""<weeklyevents><event><country>USD</country><impact>High</impact>
        <title>CPI</title><date>01-05-2026</date><time>09:30am</time>
        <forecast>2.0</forecast><actual>2.5</actual></event></weeklyevents>"""
        with patch.object(news.requests, "get", return_value=Response(200, xml)):
            result = news.compute_context(now, fetch_completed_at=now)
        self.assertTrue(result["news_valid"])
        self.assertTrue(result["news_active_window"])
        self.assertTrue(result["news_released"])
        self.assertAlmostEqual(result["news_surprise"], 0.5)
        self.assertAlmostEqual(result["news_relative_surprise"], 0.25)

    def test_delayed_fetch_uses_completion_time_and_does_not_backdate_release(self):
        request_started = datetime(2026, 1, 5, 14, 29, tzinfo=timezone.utc)
        fetched = datetime(2026, 1, 5, 14, 35, tzinfo=timezone.utc)
        xml = b"""<weeklyevents><event><country>USD</country><impact>High</impact>
        <title>CPI</title><date>01-05-2026</date><time>09:30am</time>
        <forecast>2.0</forecast><actual>2.5</actual></event></weeklyevents>"""
        with patch.object(news.requests, "get", return_value=Response(200, xml)):
            result = news.compute_context(request_started, fetch_completed_at=fetched)
        self.assertTrue(result["news_valid"])
        self.assertTrue(result["news_released"])
        self.assertEqual(result["news_observed_ts"], int(fetched.timestamp()))

    def test_fetch_completion_earlier_than_request_start_is_unavailable(self):
        request_started = datetime(2026, 1, 5, 14, 35, tzinfo=timezone.utc)
        fetched = datetime(2026, 1, 5, 14, 29, tzinfo=timezone.utc)
        with patch.object(news.requests, "get", return_value=Response(200, b"<weeklyevents/>")):
            result = news.compute_context(request_started, fetch_completed_at=fetched)
        self.assertFalse(result["news_valid"])
        self.assertEqual(result["news_observed_ts"], 0)
    def test_populated_actual_for_future_scheduled_event_is_not_released(self):
        now = datetime(2026, 1, 5, 14, 0, tzinfo=timezone.utc)
        xml = b"""<weeklyevents><event><country>USD</country><impact>High</impact>
        <title>CPI</title><date>01-05-2026</date><time>09:30pm</time>
        <forecast>2.0</forecast><actual>2.5</actual></event></weeklyevents>"""
        with patch.object(news.requests, "get", return_value=Response(200, xml)):
            result = news.compute_context(now, fetch_completed_at=now)
        self.assertTrue(result["news_valid"])
        self.assertFalse(result["news_released"])
        self.assertEqual(result["news_surprise"], 0.0)

    def test_relevant_event_without_usable_time_is_not_a_quiet_feed(self):
        xml = b"""<weeklyevents><event><country>USD</country><impact>High</impact>
        <title>FOMC</title><date>01-05-2026</date><time>All Day</time></event></weeklyevents>"""
        with patch.object(news.requests, "get", return_value=Response(200, xml)):
            self.assertIsNone(news.fetch_news_events())

    def test_eastern_calendar_conversion_observes_exact_2026_dst_boundaries(self):
        cases = [
            (datetime(2026, 3, 7, 9, 30), datetime(2026, 3, 7, 14, 30, tzinfo=timezone.utc)),
            (datetime(2026, 3, 9, 9, 30), datetime(2026, 3, 9, 13, 30, tzinfo=timezone.utc)),
            (datetime(2026, 10, 31, 9, 30), datetime(2026, 10, 31, 13, 30, tzinfo=timezone.utc)),
            (datetime(2026, 11, 2, 9, 30), datetime(2026, 11, 2, 14, 30, tzinfo=timezone.utc)),
        ]
        for local_time, expected_utc in cases:
            with self.subTest(local_time=local_time):
                self.assertEqual(news._eastern_local_to_utc(local_time), expected_utc)

    def test_dst_transition_gap_and_ambiguous_hour_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "nonexistent"):
            news._eastern_local_to_utc(datetime(2026, 3, 8, 2, 30))
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            news._eastern_local_to_utc(datetime(2026, 11, 1, 1, 30))

    def test_feed_marks_dst_transition_local_time_unavailable(self):
        xml = b"""<weeklyevents><event><country>USD</country><impact>High</impact>
        <title>CPI</title><date>03-08-2026</date><time>02:30am</time></event></weeklyevents>"""
        with patch.object(news.requests, "get", return_value=Response(200, xml)):
            self.assertIsNone(news.fetch_news_events())

    def test_schema_exports_news_observation_timestamp(self):
        ctx = ExternalContext(news_valid=True, news_observed_ts=12345)
        fields = dict(line.split("=", 1) for line in ctx.to_kv_lines().splitlines())
        self.assertEqual(fields["schema_version"], str(SCHEMA_VERSION))
        self.assertEqual(fields["news_valid"], "1")
        self.assertEqual(fields["news_observed_ts"], "12345")

    def test_external_service_copies_unavailable_status_and_rate_limits_failures(self):
        runner = (PY_ROOT / "run_external_service.py").read_text(encoding="utf-8-sig")
        self.assertIn("_last_news_fetch = now_ts", runner)
        self.assertIn('"news_valid": False', runner)
        self.assertIn('"news_observed_ts": 0', runner)
        self.assertIn("if _cached_news is not None:", runner)
        self.assertIn("if not ctx.news_valid:", runner)
        self.assertIn("ctx.data_quality |= DataQuality.EXTERNAL_ABSENT", runner)

    def test_external_service_imports_the_tracked_algomind_package(self):
        runner = (PY_ROOT / "run_external_service.py").read_text(encoding="utf-8-sig")
        self.assertIn("from algomind.schema import ExternalContext, DataQuality", runner)
        self.assertIn("from algomind.bridge.local_bridge import", runner)
        self.assertIn("from algomind.external.cftc_adapter import", runner)
        self.assertIn("from algomind.external.options_adapter import", runner)
        self.assertIn("from algomind.external.news_adapter import", runner)
        self.assertNotIn("from Amigo.", runner)


if __name__ == "__main__":
    unittest.main()
