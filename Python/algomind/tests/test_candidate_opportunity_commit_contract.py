"""Offline checks for AMIGO's at-most-once opportunity state transitions."""
from pathlib import Path


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "MQL5" / "Include" / "Risk Engine.mqh").is_file()
)
RISK = (ROOT / "MQL5" / "Include" / "Risk Engine.mqh").read_text(encoding="utf-8-sig")


def complete(outcome: int, persist_ok: bool):
    """Independent expected-state model for the durable completion boundary."""
    lock_owned = True
    if not persist_ok:
        return False, lock_owned, outcome
    if outcome == 5:  # RISK_OP_UNCERTAIN
        return True, lock_owned, outcome
    return True, False, outcome


def restart_admission_allowed(symbol_outcomes):
    """An unresolved consumed opportunity on any symbol blocks restart admission."""
    return not any(outcome in (1, 5) for outcome in symbol_outcomes)


def test_reservation_is_persisted_before_decision_can_start():
    begin = RISK.split("bool RiskBeginOpportunity(", 1)[1].split(
        "bool RiskCompleteOpportunity", 1
    )[0]
    assert begin.index("g_risk.last_opportunity_outcome=RISK_OP_RESERVED;") < begin.index(
        "if(!RiskPersist()) return false;"
    )
    assert begin.index("if(!RiskPersist()) return false;") < begin.index(
        "g_risk_opportunity_inflight=true;"
    )


def test_completion_persists_outcome_before_releasing_admission_lock():
    finish = RISK.split("bool RiskCompleteOpportunity(", 1)[1].split(
        "bool RiskTick(", 1
    )[0]
    assert finish.index("g_risk.last_opportunity_outcome=outcome;") < finish.index(
        "if(!RiskPersist()) return false;"
    )
    assert finish.index("if(!RiskPersist()) return false;") < finish.index(
        "return RiskReleaseAccountLock();"
    )
    assert "if(outcome==RISK_OP_UNCERTAIN) return true;" in finish


def test_rejected_uncertain_and_failed_persistence_have_distinct_expected_outcomes():
    assert complete(2, True) == (True, False, 2)  # rejected opportunity consumed
    assert complete(5, True) == (True, True, 5)   # uncertain outcome quarantined
    assert complete(2, False) == (False, True, 2)  # failed save retains lock


def test_restart_blocks_reserved_or_uncertain_opportunity_from_any_symbol():
    init = RISK.split("bool RiskInitLocked(", 1)[1].split("bool RiskInit(", 1)[0]
    scanner = RISK.split("int RiskLegacyOpportunityStatus()", 1)[1].split(
        "bool RiskLegacyAggregate(", 1
    )[0]
    assert "RiskLegacyOpportunityStatus()" in init
    assert init.index("if(legacy_uncertain || legacy_opportunity_status>0)") < init.index(
        "g_risk.initialized=true;"
    )
    assert "GlobalVariableSet(RiskOpportunityLockKey(),-1.0);" in init
    assert "for(int i=0;i<count;i++)" in scanner
    assert "state.last_opportunity_outcome==RISK_OP_RESERVED" in scanner
    assert "state.last_opportunity_outcome==RISK_OP_UNCERTAIN" in scanner
    assert "prefixes[i]==current_symbol_prefix" not in scanner

    assert restart_admission_allowed([])
    assert restart_admission_allowed([2, 3, 4, 6])
    assert not restart_admission_allowed([4, 5])  # uncertainty on another symbol
    assert not restart_admission_allowed([1, 4])  # crash after reserve


if __name__ == "__main__":
    test_reservation_is_persisted_before_decision_can_start()
    test_completion_persists_outcome_before_releasing_admission_lock()
    test_rejected_uncertain_and_failed_persistence_have_distinct_expected_outcomes()
    test_restart_blocks_reserved_or_uncertain_opportunity_from_any_symbol()
