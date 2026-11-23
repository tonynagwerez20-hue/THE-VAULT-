"""Offline reference-model checks distinguishing valid state advances from failure rollbacks.

Reference-model testing:
- Failed assembly / invalid geometry / stale chronology leaves accepted state untouched.
- Failed risk gate / infeasibility leaves accepted state untouched (RISK_OP_REJECTED).
- Successfully evaluated NO_TRADE commits candidate feature/regime state and advances history (RISK_OP_NO_TRADE).
- Ambiguous execution, registration failure, visibility failure, or post-fill verification failure
  quarantines admission and leaves state untouched (RISK_OP_UNCERTAIN).
- Successful shadow trade commits state and returns RISK_OP_SHADOW.
- Successful live trade fill commits state and returns RISK_OP_CONFIRMED.
- Unknown/unsupported execution outcomes raise an error / are rejected rather than assumed successful.
- FeatureVector source verification: state assignment order and non-finite numeric checks before commit.
"""

from pathlib import Path
import math
import re
import unittest

ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "MQL5" / "Experts" / "AMIGO.mq5").is_file()
)
AMIGO = (ROOT / "MQL5" / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig")
FEATURES = (ROOT / "MQL5" / "Include" / "FeatureVector.mqh").read_text(encoding="utf-8-sig")

SUPPORTED_EXECUTION_OUTCOMES = {
    "CONFIRMED_FILL",
    "SHADOW_EVALUATED",
    "AMBIGUOUS_RESULT",
    "REGISTRATION_FAILURE",
    "VISIBILITY_FAILURE",
    "POST_FILL_VERIFICATION_FAILURE",
    "RISK_REJECTED",
}

FEATURE_NUMERIC_FIELDS = [
    'atr14', 'range_ratio', 'vol_percentile', 'bos_age_bars', 'vwap',
    'dev_vwap_atr', 'poc', 'vah', 'val', 'delta_a', 'delta_b', 'fusion',
    'fvg_fill_pct', 'delta_divergence', 'divergence_bull', 'divergence_bear',
    'displacement'
]


def committed_state(previous, candidate, assembly_succeeded):
    """Independent expected transaction: failures commit no feature state."""
    return candidate if assembly_succeeded else previous


def feature_snapshot_numerics_valid(feat: dict) -> bool:
    """Independent oracle mirroring MQL5 FeatureSnapshotNumericsValid()."""
    for field in FEATURE_NUMERIC_FIELDS:
        val = feat.get(field, 0.0)
        if not isinstance(val, (int, float)) or not math.isfinite(val):
            return False
    return True


def transition_pipeline_state(initial_state: dict,
                              assembly_ok: bool,
                              candidate_feat: dict,
                              candidate_regime: int,
                              decision_action: str,  # "ACTION_NO_TRADE", "ACTION_TRADE"
                              geometry_ok: bool = True,
                              risk_allows: bool = True,
                              shadow_only: bool = False,
                              execution_outcome: str = "CONFIRMED_FILL") -> dict:
    """Exact production reference model for `OnClosedBar` state transitions:
    1. Assembly failure or non-finite features -> RISK_OP_REJECTED, state untouched.
    2. Evaluated NO_TRADE (dr.action != ACTION_TRADE) -> RISK_OP_NO_TRADE, state commits.
    3. TRADE with geometry failure -> RISK_OP_REJECTED, state untouched.
    4. TRADE with risk gate rejection -> RISK_OP_REJECTED, state untouched.
    5. Execution outcome validation: unsupported values raise ValueError (no fallback to success).
    6. TRADE with ambiguous execution -> RISK_OP_UNCERTAIN, state untouched.
    7. TRADE with position registration failure -> RISK_OP_UNCERTAIN, state untouched.
    8. TRADE with position visibility failure -> RISK_OP_UNCERTAIN, state untouched.
    9. TRADE with post-fill verification failure -> RISK_OP_UNCERTAIN, state untouched.
    10. Successful TRADE:
        - If shadow_only=True -> RISK_OP_SHADOW, state commits.
        - If shadow_only=False -> RISK_OP_CONFIRMED, state commits.
    """
    if execution_outcome not in SUPPORTED_EXECUTION_OUTCOMES:
        raise ValueError(f"Unsupported execution_outcome: {execution_outcome}")

    state = dict(initial_state)

    # Step 1: Assembly failure or non-finite feature values
    if not assembly_ok or not feature_snapshot_numerics_valid(candidate_feat):
        return {"state": state, "outcome": "RISK_OP_REJECTED", "state_advanced": False}

    # Step 2: NO_TRADE path (production returns RISK_OP_NO_TRADE and commits state)
    if decision_action != "ACTION_TRADE":
        state["feat"] = dict(candidate_feat)
        state["regime"] = candidate_regime
        state["last_evaluated_bar"] = candidate_feat.get("timestamp", 0)
        return {"state": state, "outcome": "RISK_OP_NO_TRADE", "state_advanced": True}

    # Step 3: Geometry validation failure
    if not geometry_ok:
        return {"state": state, "outcome": "RISK_OP_REJECTED", "state_advanced": False}

    # Step 4: Risk gate failure
    if not risk_allows or execution_outcome == "RISK_REJECTED":
        return {"state": state, "outcome": "RISK_OP_REJECTED", "state_advanced": False}

    # Step 5: Ambiguous execution result
    if execution_outcome == "AMBIGUOUS_RESULT":
        return {"state": state, "outcome": "RISK_OP_UNCERTAIN", "state_advanced": False}

    # Step 6: Registration, visibility, or post-fill verification failures
    if execution_outcome in ("REGISTRATION_FAILURE", "VISIBILITY_FAILURE", "POST_FILL_VERIFICATION_FAILURE"):
        return {"state": state, "outcome": "RISK_OP_UNCERTAIN", "state_advanced": False}

    # Step 7: Successful trade path
    state["feat"] = dict(candidate_feat)
    state["regime"] = candidate_regime
    state["last_evaluated_bar"] = candidate_feat.get("timestamp", 0)

    if shadow_only or execution_outcome == "SHADOW_EVALUATED":
        return {"state": state, "outcome": "RISK_OP_SHADOW", "state_advanced": True}
    else:
        return {"state": state, "outcome": "RISK_OP_CONFIRMED", "state_advanced": True}


class TestPipelineCallerStateTransitions(unittest.TestCase):
    def setUp(self):
        self.initial_state = {
            "feat": {"timestamp": 1000, "atr14": 1.5, "range_ratio": 1.0, "vol_percentile": 0.5,
                     "bos_age_bars": 3.0, "vwap": 100.0, "dev_vwap_atr": 0.2, "poc": 100.0,
                     "vah": 101.0, "val": 99.0, "delta_a": 10.0, "delta_b": 5.0, "fusion": 0.5,
                     "fvg_fill_pct": 0.0, "delta_divergence": 0.0, "divergence_bull": 0.0,
                     "divergence_bear": 0.0, "displacement": 0.1, "structure_dir": 1},
            "regime": 2,  # REGIME_TRENDING_BULL
            "last_evaluated_bar": 1000
        }
        self.candidate_feat = {
            "timestamp": 1060, "atr14": 1.6, "range_ratio": 1.1, "vol_percentile": 0.6,
            "bos_age_bars": 1.0, "vwap": 100.5, "dev_vwap_atr": 0.3, "poc": 100.2,
            "vah": 101.5, "val": 99.2, "delta_a": 12.0, "delta_b": 6.0, "fusion": 0.7,
            "fvg_fill_pct": 0.1, "delta_divergence": 0.1, "divergence_bull": 0.2,
            "divergence_bear": 0.0, "displacement": 0.3, "structure_dir": -1
        }
        self.candidate_regime = 4  # REGIME_COMPRESSION

    def test_failed_assembly_leaves_state_untouched(self):
        res = transition_pipeline_state(
            self.initial_state,
            assembly_ok=False,
            candidate_feat=self.candidate_feat,
            candidate_regime=self.candidate_regime,
            decision_action="ACTION_TRADE"
        )
        self.assertEqual(res["outcome"], "RISK_OP_REJECTED")
        self.assertFalse(res["state_advanced"])
        self.assertEqual(res["state"], self.initial_state)

    def test_non_finite_feature_rejects_and_leaves_state_untouched(self):
        """Non-finite features (NaN/Inf) must reject before any state commitment."""
        for bad_val in (float("nan"), float("inf"), float("-inf")):
            for field in ("atr14", "vwap", "fusion", "displacement"):
                bad_feat = dict(self.candidate_feat)
                bad_feat[field] = bad_val
                self.assertFalse(feature_snapshot_numerics_valid(bad_feat))

                res = transition_pipeline_state(
                    self.initial_state,
                    assembly_ok=True,
                    candidate_feat=bad_feat,
                    candidate_regime=self.candidate_regime,
                    decision_action="ACTION_NO_TRADE"
                )
                self.assertEqual(res["outcome"], "RISK_OP_REJECTED")
                self.assertFalse(res["state_advanced"])
                self.assertEqual(res["state"], self.initial_state)

    def test_successful_no_trade_commits_state_and_returns_risk_op_no_trade(self):
        """A fully evaluated NO_TRADE commits candidate globals and returns RISK_OP_NO_TRADE."""
        res = transition_pipeline_state(
            self.initial_state,
            assembly_ok=True,
            candidate_feat=self.candidate_feat,
            candidate_regime=self.candidate_regime,
            decision_action="ACTION_NO_TRADE"
        )
        self.assertEqual(res["outcome"], "RISK_OP_NO_TRADE")
        self.assertTrue(res["state_advanced"])
        self.assertEqual(res["state"]["feat"], self.candidate_feat)
        self.assertEqual(res["state"]["regime"], self.candidate_regime)
        self.assertEqual(res["state"]["last_evaluated_bar"], 1060)

    def test_geometry_failure_rolls_back_state(self):
        res = transition_pipeline_state(
            self.initial_state,
            assembly_ok=True,
            candidate_feat=self.candidate_feat,
            candidate_regime=self.candidate_regime,
            decision_action="ACTION_TRADE",
            geometry_ok=False
        )
        self.assertEqual(res["outcome"], "RISK_OP_REJECTED")
        self.assertFalse(res["state_advanced"])
        self.assertEqual(res["state"], self.initial_state)

    def test_risk_rejection_leaves_state_untouched(self):
        """Risk gate failure returns RISK_OP_REJECTED and leaves state untouched."""
        res = transition_pipeline_state(
            self.initial_state,
            assembly_ok=True,
            candidate_feat=self.candidate_feat,
            candidate_regime=self.candidate_regime,
            decision_action="ACTION_TRADE",
            risk_allows=False
        )
        self.assertEqual(res["outcome"], "RISK_OP_REJECTED")
        self.assertFalse(res["state_advanced"])
        self.assertEqual(res["state"], self.initial_state)

    def test_ambiguous_execution_quarantines_as_uncertain(self):
        """Ambiguous execution returns RISK_OP_UNCERTAIN without state advance."""
        res = transition_pipeline_state(
            self.initial_state,
            assembly_ok=True,
            candidate_feat=self.candidate_feat,
            candidate_regime=self.candidate_regime,
            decision_action="ACTION_TRADE",
            geometry_ok=True,
            execution_outcome="AMBIGUOUS_RESULT"
        )
        self.assertEqual(res["outcome"], "RISK_OP_UNCERTAIN")
        self.assertFalse(res["state_advanced"])
        self.assertEqual(res["state"], self.initial_state)

    def test_registration_failure_is_uncertain(self):
        """Position registration failure returns RISK_OP_UNCERTAIN without state advance."""
        res = transition_pipeline_state(
            self.initial_state,
            assembly_ok=True,
            candidate_feat=self.candidate_feat,
            candidate_regime=self.candidate_regime,
            decision_action="ACTION_TRADE",
            geometry_ok=True,
            execution_outcome="REGISTRATION_FAILURE"
        )
        self.assertEqual(res["outcome"], "RISK_OP_UNCERTAIN")
        self.assertFalse(res["state_advanced"])
        self.assertEqual(res["state"], self.initial_state)

    def test_visibility_and_post_fill_failures_are_uncertain(self):
        """Visibility and post-fill aggregate risk failures return RISK_OP_UNCERTAIN without state advance."""
        for outcome in ("VISIBILITY_FAILURE", "POST_FILL_VERIFICATION_FAILURE"):
            res = transition_pipeline_state(
                self.initial_state,
                assembly_ok=True,
                candidate_feat=self.candidate_feat,
                candidate_regime=self.candidate_regime,
                decision_action="ACTION_TRADE",
                geometry_ok=True,
                execution_outcome=outcome
            )
            self.assertEqual(res["outcome"], "RISK_OP_UNCERTAIN")
            self.assertFalse(res["state_advanced"])
            self.assertEqual(res["state"], self.initial_state)

    def test_unsupported_execution_outcome_raises_error(self):
        """Unsupported/unknown execution outcome values must be rejected, not assumed successful."""
        with self.assertRaises(ValueError):
            transition_pipeline_state(
                self.initial_state,
                assembly_ok=True,
                candidate_feat=self.candidate_feat,
                candidate_regime=self.candidate_regime,
                decision_action="ACTION_TRADE",
                geometry_ok=True,
                execution_outcome="SOME_UNKNOWN_RESULT"
            )

    def test_successful_shadow_trade_advances_state_and_returns_risk_op_shadow(self):
        """Successful shadow-evaluated trade commits state and returns RISK_OP_SHADOW."""
        res = transition_pipeline_state(
            self.initial_state,
            assembly_ok=True,
            candidate_feat=self.candidate_feat,
            candidate_regime=self.candidate_regime,
            decision_action="ACTION_TRADE",
            geometry_ok=True,
            shadow_only=True,
            execution_outcome="SHADOW_EVALUATED"
        )
        self.assertEqual(res["outcome"], "RISK_OP_SHADOW")
        self.assertTrue(res["state_advanced"])
        self.assertEqual(res["state"]["feat"], self.candidate_feat)
        self.assertEqual(res["state"]["regime"], self.candidate_regime)
        self.assertEqual(res["state"]["last_evaluated_bar"], 1060)

    def test_successful_confirmed_fill_advances_state_and_returns_risk_op_confirmed(self):
        """Confirmed broker fill commits state and returns RISK_OP_CONFIRMED."""
        res = transition_pipeline_state(
            self.initial_state,
            assembly_ok=True,
            candidate_feat=self.candidate_feat,
            candidate_regime=self.candidate_regime,
            decision_action="ACTION_TRADE",
            geometry_ok=True,
            shadow_only=False,
            execution_outcome="CONFIRMED_FILL"
        )
        self.assertEqual(res["outcome"], "RISK_OP_CONFIRMED")
        self.assertTrue(res["state_advanced"])
        self.assertEqual(res["state"]["feat"], self.candidate_feat)
        self.assertEqual(res["state"]["regime"], self.candidate_regime)
        self.assertEqual(res["state"]["last_evaluated_bar"], 1060)

    def test_source_wiring_confirms_no_trade_commits_globals(self):
        """Verify AMIGO.mq5 explicitly commits candidate globals on dr.action != ACTION_TRADE and returns RISK_OP_NO_TRADE."""
        no_trade_block = AMIGO.split("if(dr.action != ACTION_TRADE)", 1)[1].split("return RISK_OP_NO_TRADE;", 1)[0]
        self.assertIn("g_snap = candidate_snap;", no_trade_block)
        self.assertIn("g_feat = candidate_feat;", no_trade_block)
        self.assertIn("g_amigo_feature_state = candidate_feature_state;", no_trade_block)
        self.assertIn("g_regime_state = candidate_regime;", no_trade_block)
        self.assertIn("CommitFlowOpportunityDiagnostics(", no_trade_block)

    def test_feature_state_assignments_are_only_at_successful_function_end(self):
        """Restored check: state assignments in BuildFeatureVector only happen at successful function exit."""
        function = FEATURES.split(
            "bool BuildFeatureVector(const string symbol, const AmigoConfig &cfg,\n"
            "                        FeatureSnapshot &fs, AMIGOFeatureState &state,",
            1,
        )[1].split("// Compatibility entry point", 1)[0]
        commit = function.index("state.structure_direction = s_prev_dir;")

        self.assertIn("int next_pressure_state=state.pressure_state;", function)
        self.assertIn("next_pressure_state=fs.pressure_state;", function)
        self.assertIn("next_pressure_state=0;", function)
        self.assertIn("state.pressure_state = next_pressure_state;", function)
        self.assertGreater(function.index("state.pressure_state = next_pressure_state;"), commit)
        early_state_assignments = re.findall(
            r"state\.(?:pressure_state|structure_direction)\s*=(?!=)",
            function[:commit],
        )
        self.assertEqual(early_state_assignments, [])
        self.assertLess(function.rindex("return false;"), commit)

        previous = {"structure_direction": -1, "pressure_state": 1}
        candidate = {"structure_direction": 1, "pressure_state": -1}
        self.assertEqual(committed_state(previous, candidate, False), previous)
        self.assertEqual(committed_state(previous, candidate, True), candidate)

    def test_all_computed_feature_doubles_are_finite_before_state_commit(self):
        """Restored check: FeatureSnapshotNumericsValid checks all double fields before commit."""
        function = FEATURES.split(
            "bool BuildFeatureVector(const string symbol, const AmigoConfig &cfg,\n"
            "                        FeatureSnapshot &fs, AMIGOFeatureState &state,",
            1,
        )[1].split("// Compatibility entry point", 1)[0]
        commit = function.index("state.structure_direction = s_prev_dir;")
        valid_call = function.index("FeatureSnapshotNumericsValid(fs)")
        self.assertLess(valid_call, commit)

        numerics_fn = FEATURES.split("FeatureSnapshotNumericsValid(const FeatureSnapshot &fs)", 1)[1].split("}", 1)[0]
        for field in FEATURE_NUMERIC_FIELDS:
            self.assertIn(f"fs.{field}", numerics_fn)
            self.assertIn(f"MathIsValidNumber(fs.{field})", numerics_fn)


if __name__ == "__main__":
    unittest.main()
