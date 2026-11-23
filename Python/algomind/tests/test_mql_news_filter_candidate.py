"""Offline contract checks for the MQL5 NEWS admission gate.

The Python decision table is an independent oracle; source assertions verify
that the MQL5 call site enforces it before mutable session/strategy work.
These tests do not execute or compile MQL5.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
EXPERT = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")
CONTEXT = (ROOT / "MQL5" / "Include" / "External Context Compactor.mqh").read_text(encoding="utf-8-sig")


def filter_oracle(mode, valid, observed, event, active, released, now, max_age):
    if mode == 0:
        return True, "OFF"
    if mode not in (1,2,3):
        return False, "NEWS_MODE_UNSUPPORTED"
    if (now <= 0 or max_age <= 0 or not valid or observed <= 0 or observed > now or now - observed > max_age
            or event < 0 or (released and event > now)):
        return False, "NEWS_UNAVAILABLE_OR_STALE"
    if mode==2 and not active:
        return False, "NEWS_NO_RELEASE_SETUP"
    if active:
        return False, "NEWS_ACTIVE_WINDOW"
    return True, "HEALTHY_NO_ACTIVE_EVENT"


def context_provider_validity(timestamp, now, max_age):
    """Independent boundary oracle for UTC context-file freshness."""
    return max_age > 0 and timestamp > 0 and timestamp <= now and now - timestamp <= max_age


class MqlNewsFilterCandidate(unittest.TestCase):
    def test_independent_policy_table(self):
        base = dict(valid=True, observed=990, event=0, active=False,
                    released=False, now=1000, max_age=30)
        self.assertEqual(filter_oracle(0, **dict(base, valid=False, observed=0))[0], True)
        self.assertEqual(filter_oracle(1, **base), (True, "HEALTHY_NO_ACTIVE_EVENT"))
        self.assertEqual(filter_oracle(1, **dict(base, active=True)), (False, "NEWS_ACTIVE_WINDOW"))
        self.assertEqual(filter_oracle(1, **dict(base, valid=False)), (False, "NEWS_UNAVAILABLE_OR_STALE"))
        self.assertEqual(filter_oracle(1, **dict(base, observed=950)), (False, "NEWS_UNAVAILABLE_OR_STALE"))
        self.assertEqual(filter_oracle(1, **dict(base, observed=1001)), (False, "NEWS_UNAVAILABLE_OR_STALE"))
        self.assertEqual(filter_oracle(1, **dict(base, now=0)), (False, "NEWS_UNAVAILABLE_OR_STALE"))
        self.assertEqual(filter_oracle(1, **dict(base, max_age=0)), (False, "NEWS_UNAVAILABLE_OR_STALE"))
        self.assertEqual(filter_oracle(2, **base), (False, "NEWS_NO_RELEASE_SETUP"))

    def test_mql_helper_checks_availability_freshness_and_active_event(self):
        helper = (ROOT / "MQL5/Include/News Policy.mqh").read_text()
        for token in ("mode==0", "mode>3", "ctx.news_valid", "ctx.news_observed_ts",
                      "ctx.news_active_window", "NEWS_UNAVAILABLE_OR_STALE",
                      "NEWS_ACTIVE_WINDOW"):
            self.assertIn(token, helper)

    def test_decision_gate_precedes_mutable_session_profile_state(self):
        on_closed = EXPERT.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        gate = on_closed.index("ExternalNewsFilterAllows(")
        first_commit = on_closed.index("CommitFlowOpportunityDiagnostics(")
        self.assertLess(gate, first_commit)
        self.assertIn("return RISK_OP_REJECTED;", on_closed[gate:first_commit])
        helper = EXPERT.split("void CommitFlowOpportunityDiagnostics(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("g_pressure_engine.UpdateState", helper)
        self.assertIn("g_events_engine.AddBar", helper)

    def test_utc_bridge_timestamps_are_compared_using_gmt_clock(self):
        on_tick = EXPERT.split("void OnTick()", 1)[1].split("int OnClosedBar(", 1)[0]
        self.assertIn("datetime ext_now=TimeGMT();", on_tick)
        self.assertIn("ExternalNewsFilterAllows(g_ext,g_cfg.news_mode,TimeGMT(),", EXPERT)
        read_context = CONTEXT.split("bool ReadExternalContext(", 1)[1].split("bool ExternalNewsFilterAllows(", 1)[0]
        self.assertIn("datetime now = TimeGMT();", read_context)

    def test_context_freshness_contract_rejects_missing_future_and_stale_times(self):
        self.assertTrue(context_provider_validity(990, 1000, 20))
        self.assertFalse(context_provider_validity(0, 1000, 20))
        self.assertFalse(context_provider_validity(1001, 1000, 20))
        self.assertFalse(context_provider_validity(900, 1000, 20))
        self.assertFalse(context_provider_validity(990, 1000, 0))
        read_context = CONTEXT.split("bool ReadExternalContext(", 1)[1].split(
            "bool ExternalNewsFilterAllows(", 1)[0]
        self.assertIn("const int max_age_seconds=120", read_context)
        self.assertIn("datetime now = TimeGMT();", read_context)
        self.assertIn("(now-ctx.timestamp)>max_age_seconds", read_context)
        self.assertNotIn("FileGetInteger(path, FILE_MODIFY_DATE", read_context)
        for token in ("ctx.cftc_valid=false;", "ctx.options_valid=false;", "ctx.news_valid=false;"):
            self.assertIn(token, read_context)
        self.assertIn("ReadExternalContext(g_cfg.bridge_inbox, tmp, err,g_cfg.stale_threshold_s)", EXPERT)

    def test_unknown_schema_invalidates_every_provider(self):
        read_context = CONTEXT.split("bool ReadExternalContext(", 1)[1].split(
            "bool ExternalNewsFilterAllows(", 1)[0]
        mismatch = read_context.split("if(ctx.schema_version != Amigo_SCHEMA_VERSION)", 1)[1].split(
            "//--- Point-in-time correctness", 1)[0]
        for token in ("ctx.cftc_valid = false;", "ctx.options_valid = false;",
                      "ctx.news_valid = false;", "DQ_SCHEMA_MISMATCH"):
            self.assertIn(token, mismatch)

    def test_news_buffer_is_one_fixed_cross_language_contract(self):
        config = (ROOT / "MQL5" / "Include" / "Configuration.mqh").read_text(encoding="utf-8-sig")
        on_init = EXPERT.split("int OnInit()", 1)[1].split("void OnDeinit", 1)[0]
        runner = (ROOT / "Python" / "run_external_service.py").read_text(encoding="utf-8-sig")
        adapter = (ROOT / "Python" / "algomind" / "external" / "news_adapter.py").read_text(encoding="utf-8-sig")
        self.assertIn("#define AMIGO_NEWS_BUFFER_MINUTES 30", config)
        self.assertIn("InpNewsBufferMins!=AMIGO_NEWS_BUFFER_MINUTES", on_init)
        self.assertIn("g_cfg.news_buffer_mins    = AMIGO_NEWS_BUFFER_MINUTES", on_init)
        self.assertIn("DEFAULT_BUFFER_MINUTES = 30", adapter)
        self.assertIn("buffer_minutes=DEFAULT_BUFFER_MINUTES", runner)


if __name__ == "__main__":
    unittest.main()
