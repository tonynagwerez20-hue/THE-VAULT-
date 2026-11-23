"""Offline source-contract checks for closed-bar snapshot identity."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = (ROOT / "MQL5" / "Include" / "Contracts header.mqh").read_text(encoding="utf-8-sig")
BUILDER = (ROOT / "MQL5" / "Include" / "Market Snapshot Builder.mqh").read_text(encoding="utf-8-sig")
FEATURE = (ROOT / "MQL5" / "Include" / "FeatureVector.mqh").read_text(encoding="utf-8-sig")
STRUCTURE = (ROOT / "MQL5" / "Include" / "Structure Engine.mqh").read_text(encoding="utf-8-sig")
REGIME = (ROOT / "MQL5" / "Include" / "Regime Engine.mqh").read_text(encoding="utf-8-sig")
STRATEGY = (ROOT / "MQL5" / "Include" / "Strategy Engine.mqh").read_text(encoding="utf-8-sig")
AMIGO = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")


class SnapshotIdentityCandidateTests(unittest.TestCase):
    def test_identity_and_closed_boundary_fields_exist_across_pipeline(self):
        for text in (CONTRACTS, REGIME, STRATEGY):
            self.assertIn("snapshot_id", text)
        self.assertIn("datetime decision_boundary", CONTRACTS)
        self.assertIn("datetime closed_bar_time", CONTRACTS)
        self.assertIn("datetime asof_boundary", STRUCTURE)

    def test_builder_rechecks_requested_boundary_and_latest_closed_bar(self):
        self.assertIn("decision_timeframe,0)!=decision_boundary", BUILDER)
        self.assertIn("decision_timeframe,1)!=closed_bar_time", BUILDER)
        self.assertIn("decision_boundary,", AMIGO)

    def test_strategy_pipeline_rejects_identity_or_boundary_mismatch(self):
        self.assertIn("candidate_feat.snapshot_id=opportunity_id", AMIGO)
        self.assertIn("td.asof_boundary!=decision_boundary", AMIGO)
        self.assertIn("rs.snapshot_id!=opportunity_id", AMIGO)
        self.assertIn("dr.snapshot_id!=opportunity_id", AMIGO)
        self.assertIn("ti.snapshot_id      = dr.snapshot_id", AMIGO)

    def test_features_and_mtf_are_rechecked_before_regime_and_decision(self):
        on_closed = AMIGO.split("int OnClosedBar(", 1)[1].split("void OnTradeTransaction(", 1)[0]
        self.assertLess(on_closed.index("if(!feat_res)"), on_closed.index("candidate_feat.snapshot_id=opportunity_id"))
        self.assertLess(on_closed.index("td.asof_boundary!=decision_boundary"), on_closed.index("EvaluateRegimeWithState"))
        self.assertLess(on_closed.index("dr.snapshot_id!=opportunity_id"), on_closed.index("TradeIntent ti;"))


if __name__ == "__main__":
    unittest.main()
