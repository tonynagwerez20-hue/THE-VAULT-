"""Source integration assertions; these do not execute MQL5 or prove disk durability.

Independent contract: once a fill is proven and visible, its management record
must survive a subsequent exposure rejection. Neither persistence failure nor
exposure failure may commit accepted strategy state or return CONFIRMED.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPERT = (ROOT / "MQL5/Experts/AMIGO.mq5").read_text()
MANAGER = (ROOT / "MQL5/Include/Position Manager.mqh").read_text()


def live_path():
    return EXPERT.split("if(!g_cfg.shadow_only && er.accepted)", 1)[1].split(
        "// Single accepted-state commit point", 1)[0]


def test_registration_persistence_failure_stops_before_risk_and_strategy_commit():
    body = live_path()
    registration = body.index("PositionManagerRegister(er.position_id")
    failed_save_guard = body.index(
        "if(!PositionManagerAdmissionAllowed()) return RISK_OP_UNCERTAIN;", registration)
    assert registration < failed_save_guard < body.index("AccountEstimatedStopRisk(")
    register_body = MANAGER.split("void PositionManagerRegister(", 1)[1].split(
        "void PositionManagerRemove(", 1)[0]
    assert 'if(!PositionSaveState(cfg))' in register_body
    assert 'PositionManagerLatchStateFault("position registration was not durably saved")' in register_body


def test_all_postfill_risk_failures_preserve_record_and_quarantine():
    body = live_path()
    registered, risk = body.split("double reconciled_stop_risk=0.0;", 1)
    assert registered.count("PositionManagerRegister(er.position_id") == 1
    # Invalid equity, unreadable exposure, invalid sum, or the 2% breach all
    # take the same quarantine exit AFTER registration, with no record removal.
    for condition in ("reconciled_equity<=0.0", "!AccountEstimatedStopRisk(",
                      "!MathIsValidNumber(reconciled_stop_risk)",
                      ">AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT"):
        assert condition in risk
    assert 'PositionManagerLatchStateFault("post-fill aggregate stop-risk verification failed:' in risk
    assert 'return RISK_OP_UNCERTAIN;' in risk
    assert 'PositionManagerRemove' not in risk
    assert 'ArrayResize' not in risk
    assert 'g_snap = candidate_snap' not in risk
    assert 'RISK_OP_CONFIRMED' not in risk
