"""Offline contract checks for staged order-flow diagnostic state.

The reference state machine is independently specified here; source assertions
check only that MQL wires the reset to accepted-opportunity commit points.
They do not execute MQL5 or validate terminal behavior.
"""
from pathlib import Path
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Experts" / "AMIGO.mq5").is_file())
EXPERT = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")


def tick_session_transition(initialized, was_in_session, prior_tag, in_session, current_tag):
    """Partition the rolling tick collector before ingesting the new session tick."""
    reset = in_session and (not initialized or not was_in_session or prior_tag != current_tag)
    return reset, (True, in_session, current_tag if in_session else prior_tag)


class FlowSessionCommitCandidate(unittest.TestCase):
    def test_streaming_session_reset_precedes_new_tick_ingestion(self):
        reset, state = tick_session_transition(False, False, -1, True, 42)
        self.assertTrue(reset)
        self.assertEqual(state, (True, True, 42))
        reset, state = tick_session_transition(*state, True, 42)
        self.assertFalse(reset)
        self.assertEqual(state, (True, True, 42))
        on_tick = EXPERT.split("void OnTick()", 1)[1].split("int OnClosedBar(", 1)[0]
        self.assertLess(on_tick.index("g_footprint_engine.Reset();"),
                        on_tick.index("g_footprint_engine.AddTick("))
        self.assertLess(on_tick.index("g_vwap_engine.Reset();"),
                        on_tick.index("g_vwap_engine.AddObservation("))

    def test_per_bar_flow_state_mutates_only_at_accepted_outcome(self):
        helper = EXPERT.split("void CommitFlowOpportunityDiagnostics(", 1)[1].split("\n}\n", 1)[0]
        on_closed = EXPERT.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        self.assertIn("g_pressure_engine.UpdateState", helper)
        self.assertIn("g_events_engine.AddBar", helper)
        self.assertNotIn("g_pressure_engine.UpdateState", on_closed)
        self.assertNotIn("g_events_engine.AddBar", on_closed)
        self.assertEqual(EXPERT.count("CommitFlowOpportunityDiagnostics("), 3)

    def test_commit_calls_are_after_no_trade_or_full_trade_acceptance(self):
        on_closed = EXPERT.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        calls = [i for i in range(len(on_closed))
                 if on_closed.startswith("CommitFlowOpportunityDiagnostics(", i)]
        self.assertEqual(len(calls), 2)
        self.assertGreater(calls[0], on_closed.index("if(dr.action != ACTION_TRADE)"))
        self.assertGreater(calls[1], on_closed.index("if(!PositionManagerAdmissionAllowed()) return RISK_OP_UNCERTAIN;"))

    def test_session_transition_and_diagnostic_mutation_are_separate_contracts(self):
        self.assertIn("tick_session_started", EXPERT)
        self.assertIn("g_flow_last_session_open_epoch!=tick_session_tag", EXPERT)
        self.assertIn("if(InpEnableTickPressure)", EXPERT)


if __name__ == "__main__":
    unittest.main()
