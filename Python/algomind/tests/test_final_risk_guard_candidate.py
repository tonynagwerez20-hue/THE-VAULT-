"""Offline contract tests for AMIGO's estimated stop-loss gate.

These tests check source ordering and independently derived threshold examples;
they do not execute MQL5 OrderCalcProfit or represent realized loss.
"""
from math import isfinite
from pathlib import Path
import re
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Include").is_dir())
ACCOUNT = (ROOT / "MQL5" / "Include" / "Account Execution Engine.mqh").read_text(encoding="utf-8-sig")
EXECUTION = (ROOT / "MQL5" / "Include" / "Execution Engine.mqh").read_text(encoding="utf-8-sig")
RISK = (ROOT / "MQL5" / "Include" / "RiskController.mqh").read_text(encoding="utf-8-sig")
AMIGO = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")


def admits(equity, estimated_loss):
    return (isfinite(equity) and equity > 0 and isfinite(estimated_loss)
            and estimated_loss > 0 and estimated_loss / equity * 100 <= 2.0)


def distortion_admits(equity, effective_risk_pct, max_distortion, estimated_loss):
    """Independent final-quote oracle uses current equity and the sizing policy."""
    values = (equity, effective_risk_pct, max_distortion, estimated_loss)
    return (all(isfinite(x) for x in values) and equity > 0 and
            0 < effective_risk_pct <= 2.0 and max_distortion > 0 and
            estimated_loss > 0 and
            estimated_loss / (equity * effective_risk_pct / 100.0)
            <= max_distortion + 0.00001)


class FinalRiskGuardCandidate(unittest.TestCase):
    def test_canonical_tier_anchors_are_preserved(self):
        block = RISK.split("static RiskControlPoint g_risk_curve[RISK_SPLINE_POINTS] = {", 1)[1].split("};", 1)[0]
        rows = re.findall(r"\{\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\}", block)
        expected = [
            (10.0, 1.50, 5.0), (50.0, 1.25, 4.0), (100.0, 1.00, 3.5),
            (250.0, 0.75, 3.0), (500.0, 0.50, 2.5), (1000.0, 0.50, 2.0),
            (5000.0, 0.50, 1.5), (10000.0, 0.50, 1.0),
        ]
        self.assertEqual([tuple(map(float, row)) for row in rows], expected)

    def test_sized_volume_loss_checked_before_margin(self):
        marker = "OrderCalcProfit(risk_order_type, symbol, env.executable_volume, entry, stop, stop_profit)"
        self.assertIn(marker, ACCOUNT)
        self.assertLess(ACCOUNT.index("AccountVolumeFloorToStep(env.raw_volume"), ACCOUNT.index(marker))
        self.assertLess(ACCOUNT.index(marker), ACCOUNT.index("//--- 9. Margin Verification"))
        self.assertIn('env.reason                   = "ESTIMATED_STOP_RISK_ABOVE_2PCT";', ACCOUNT)

    def test_refreshed_request_checked_before_any_send_path(self):
        marker = "OrderCalcProfit(req.type, req.symbol, req.volume, req.price, req.sl, request_stop_profit)"
        self.assertIn(marker, EXECUTION)
        self.assertLess(EXECUTION.index(marker), EXECUTION.index("if(!OrderCheck(req, chk))"))
        self.assertLess(EXECUTION.index(marker), EXECUTION.index("OrderSend(req, res)"))

    def test_refreshed_quote_must_retain_approved_distortion_limit(self):
        # $1,000 equity at 0.5% target means $5 target risk; 1.5x permits $7.50.
        # A refreshed quote can move estimated risk above that tier limit while
        # remaining below the independent 2% absolute ceiling.
        self.assertTrue(distortion_admits(1000, 0.5, 1.5, 7.5))
        self.assertFalse(distortion_admits(1000, 0.5, 1.5, 7.5001))
        self.assertTrue(admits(1000, 7.5001))
        self.assertFalse(distortion_admits(1000, 0.5, 1.5, 7.5001))
        self.assertIn("FINAL_REQUEST_RISK_DISTORTION_ABOVE_POLICY", EXECUTION)
        call=AMIGO.split("ExecutionResult er = ExecuteIntent(ti, lots, g_cfg, stop_dist,", 1)[1].split(");", 1)[0]
        self.assertIn("effective_risk_pct", call)
        self.assertIn("risk_auto.max_allowed_distortion", call)
        signature=EXECUTION.split("ExecutionResult ExecuteIntent(", 1)[1].split("\n{", 1)[0]
        self.assertIn("const double authorized_risk_pct", signature)
        self.assertIn("const double max_allowed_distortion", signature)
        self.assertNotIn("=0.0", signature)
        self.assertIn("10.0, 0.50, 5.0", (ROOT / "MQL5" / "Scripts" / "Test_ShadowHarness.mq5").read_text(encoding="utf-8-sig"))
        distortion_check=EXECUTION.index("FINAL_REQUEST_RISK_DISTORTION_ABOVE_POLICY")
        self.assertLess(distortion_check, EXECUTION.index("if(!OrderCheck(req, chk))"))
        self.assertLess(distortion_check, EXECUTION.index("OrderSend(req, res)"))

    def test_missing_or_invalid_final_risk_policy_fails_closed(self):
        self.assertFalse(distortion_admits(1000, 0.0, 1.5, 1.0))
        self.assertFalse(distortion_admits(1000, 0.5, 0.0, 1.0))
        self.assertFalse(distortion_admits(1000, float("nan"), 1.5, 1.0))
        self.assertIn('"FINAL_RISK_POLICY_UNAVAILABLE"', EXECUTION)

    def test_independent_threshold_examples(self):
        self.assertTrue(admits(100.0, 2.0))
        self.assertFalse(admits(100.0, 2.000001))
        self.assertTrue(admits(16.15, 0.32))
        self.assertFalse(admits(16.15, 0.89))

    def test_nonfinite_or_nonpositive_inputs_fail_closed(self):
        for equity, loss in ((0.0, 1.0), (-1.0, 1.0), (100.0, 0.0),
                             (100.0, -1.0), (float("nan"), 1.0),
                             (100.0, float("inf"))):
            with self.subTest(equity=equity, loss=loss):
                self.assertFalse(admits(equity, loss))

    def test_invalid_regime_modifier_rejects_before_risk_sizing(self):
        start = AMIGO.index("double reg_mod = rs.risk_modifier;")
        end = AMIGO.index("double effective_risk_pct =", start)
        gate = AMIGO[start:end]
        self.assertIn("!MathIsValidNumber(reg_mod)", gate)
        self.assertIn('"RISK_MODIFIER_INVALID"', gate)
        self.assertIn("return RISK_OP_REJECTED;", gate)
        self.assertNotIn("reg_mod = 1.00", gate)

    def test_intent_records_adaptive_risk_separately_from_regime_modifier(self):
        self.assertIn("effective_risk_pct = risk_auto.effective_risk_percent * reg_mod", AMIGO)
        self.assertIn("ti.risk_allocation  = risk_auto.effective_risk_percent;", AMIGO)
        self.assertIn("ti.risk_modifier    = reg_mod;", AMIGO)
        self.assertIn("risk_allocation; // Account-adaptive target risk percent before regime modifier",
                      (ROOT / "MQL5" / "Include" / "Contracts header.mqh").read_text(encoding="utf-8-sig"))

    def test_adaptive_stop_uses_loss_tick_value_and_first_legal_volume(self):
        stop_engine = (ROOT / "MQL5" / "Include" / "Risk Engine.mqh").read_text(encoding="utf-8-sig")
        block = stop_engine.split("AdaptiveSLResult EvaluateAdaptiveStop(", 1)[1]
        self.assertIn("AccountSymbolLossTickValue(symbol)", block)
        self.assertIn("AccountVolumeCeilToStep(vol_min,vol_step)", block)
        self.assertIn("max_valid_volume<min_valid_volume", block)
        audit_block = AMIGO.split("//--- Task 1 & 2: Complete Empirical Runtime Symbol & OrderCalcProfit Audit", 1)[1].split("return INIT_SUCCEEDED;", 1)[0]
        self.assertIn("AccountSymbolLossTickValue(g_symbol)", audit_block)
        self.assertIn("AccountVolumeCeilToStep(v_min,v_step)", audit_block)
        self.assertIn("v_min_valid, 2000.0, 2000.0 - st_d", audit_block)


if __name__ == "__main__":
    unittest.main()
