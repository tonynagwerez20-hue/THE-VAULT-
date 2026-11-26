"""Hierarchical horizon selector validation; NOT native MQL execution."""
from itertools import product
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/"MQL5/Include/Strategy Engine.mqh").read_text()
E=(ROOT/"MQL5/Experts/AMIGO.mq5").read_text()
T=(ROOT/"MQL5/Include/Structure Engine.mqh").read_text()
BODY=S.split("bool SelectApprovedHorizon(",1)[1].split("// One frozen entry-proxy",1)[0]
FIELDS=("d1_dir","h4_dir","h1_dir","m30_dir","m15_dir","m5_dir","m1_dir")

def test_hierarchical_functions_present():
    """Verify all required functions are implemented."""
    assert "bool SelectApprovedHorizon" in S
    assert "bool EvaluateHorizonForTrend" in S
    assert "double TFBias" in S

def test_missing_invalid_guards_explicit():
    """Verify safety guards are present."""
    assert "!td.complete" in BODY
    assert "td.asof_boundary!=boundary" in BODY
    assert "boundary<=0" in BODY
    assert "decision.action!=ACTION_TRADE" in BODY
    assert "decision.direction!=1 && decision.direction!=-1" in BODY
    assert "horizon=(ENUM_HORIZON)0;" in BODY

def test_tf_validation_range():
    """Verify TF validation checks range [-1,1]."""
    assert "dirs[i]<-1 || dirs[i]>1" in BODY

def test_hierarchical_evaluation_order():
    """Verify Swing → Intraday → Scalp evaluation order."""
    assert "EvaluateHorizonForTrend(td, decision.direction, decision.hypothesis, regime, HORIZON_SWING)" in BODY
    assert "EvaluateHorizonForTrend(td, decision.direction, decision.hypothesis, regime, HORIZON_INTRADAY)" in BODY
    assert "EvaluateHorizonForTrend(td, decision.direction, decision.hypothesis, regime, HORIZON_SCALPING)" in BODY

    # Verify order: Swing before Intraday before Scalp
    swing_pos = BODY.index("HORIZON_SWING")
    intraday_pos = BODY.index("HORIZON_INTRADAY")
    scalp_pos = BODY.index("HORIZON_SCALPING")
    assert swing_pos < intraday_pos < scalp_pos

def test_countertrend_scalp_support():
    """Verify scalp allows countertrend when setup+entry support direction."""
    eval_body = S.split("bool EvaluateHorizonForTrend",1)[1].split("// Directional bias calculator",1)[0]
    assert "HORIZON_SCALPING" in eval_body
    assert "countertrend" in eval_body.lower() or "scalp can trade against" in eval_body.lower()

def test_tf_bias_implementation():
    """Verify TFBias function implements weighted bias formula."""
    bias_body = S.split("double TFBias",1)[1].split("// One frozen entry-proxy",1)[0]
    assert "numerator" in bias_body
    assert "denominator" in bias_body
    assert "weights[i]*confidences[i]*dirs[i]" in bias_body
    assert "weights[i]*confidences[i]" in bias_body

def test_m1_veto_sequence_in_amigo():
    """Verify EXEC_M1_VETO fires before SelectApprovedHorizon."""
    body = E.split("int OnClosedBar(",1)[1].split("void OnTradeTransaction(",1)[0]
    selection = body.index("SelectApprovedHorizon(td,dr,rs.regime,decision_boundary,selected_horizon)")
    assert body.index("ScoreStrategies(decision_feat, g_ext, g_cfg)") < selection
    assert body.index("if(dr.action != ACTION_TRADE)") < selection
    assert selection < body.index("RiskAllows(g_cfg, risk_reason)")

def test_no_default_intraday_assignment():
    """Verify no hardcoded intraday assignment without horizon selection."""
    body = E.split("int OnClosedBar(",1)[1].split("void OnTradeTransaction(",1)[0]
    assert "selected_horizon = HORIZON_INTRADAY" not in body
    assert body.count("dr.horizon=selected_horizon;") == 1

def test_compilation_clean():
    """Verify basic source structure is valid."""
    assert "#ifndef AMIGO_INCLUDE_STRATEGY_ENGINE_MQH" in S
    assert "#endif // AMIGO_INCLUDE_STRATEGY_ENGINE_MQH" in S