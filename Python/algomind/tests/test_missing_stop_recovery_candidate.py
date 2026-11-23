"""Offline contract checks for restoring only previously confirmed stops.

No MQL5 runtime or broker position is exercised by this test module.
"""
from pathlib import Path

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "MQL5" / "Include").is_dir()) / "MQL5"
RECOVERY = (ROOT / "Include" / "PositionRecovery.mqh").read_text(encoding="utf-8-sig")
MANAGER = (ROOT / "Include" / "Position Manager.mqh").read_text(encoding="utf-8-sig")


def recovery_action(direction, broker_stop, current_stop, last_stop, initial_stop,
                    current_price, minimum_distance):
    """Independent policy oracle: retain ratchet; restore only if still legal."""
    if direction not in (-1, 1) or current_price is None or current_price <= 0:
        return "QUARANTINE"
    candidates = [x for x in (current_stop, last_stop, initial_stop)
                  if x is not None and x > 0]
    if not candidates:
        return "QUARANTINE"
    target = max(candidates) if direction == 1 else min(candidates)
    if broker_stop is not None and broker_stop > 0:
        already_crossed = current_price <= broker_stop if direction == 1 else current_price >= broker_stop
        at_least_as_tight = broker_stop >= target if direction == 1 else broker_stop <= target
        if already_crossed:
            return "QUARANTINE"
        if at_least_as_tight:
            return "KEEP"
    distance = current_price - target if direction == 1 else target - current_price
    if distance < minimum_distance:
        return "QUARANTINE"
    return "RESTORE"


def admission_after_repair(generic_fault, repair_required, all_positions_protected):
    if repair_required and all_positions_protected:
        repair_required = False
    return not generic_fault and not repair_required


def test_independent_long_and_short_stop_recovery_expectations():
    assert recovery_action(1, 0, 99, 99, 98, 100, 0.5) == "RESTORE"
    assert recovery_action(-1, 0, 101, 101, 102, 100, 0.5) == "RESTORE"
    assert recovery_action(1, 99.5, 99, 99, 98, 100, 0.5) == "KEEP"
    assert recovery_action(-1, 100.5, 101, 101, 102, 100, 0.5) == "KEEP"


def test_weaker_stop_never_replaces_a_tighter_confirmed_ratchet():
    assert recovery_action(1, 98, 99, 99.5, 97, 100, 0.25) == "RESTORE"
    assert recovery_action(-1, 102, 101, 100.5, 103, 100, 0.25) == "RESTORE"


def test_crossed_or_unrestorable_stop_quarantines_instead_of_guessing():
    assert recovery_action(1, 0, 99, 99, 98, 98.5, 0.25) == "QUARANTINE"
    assert recovery_action(-1, 0, 101, 101, 102, 101.5, 0.25) == "QUARANTINE"
    assert recovery_action(1, 0, 99, 99, 98, 99.1, 0.25) == "QUARANTINE"
    assert recovery_action(1, 0, 0, 0, 0, 100, 0.25) == "QUARANTINE"
    assert recovery_action(1, 0, 99, 99, 98, None, 0.25) == "QUARANTINE"


def test_recovery_preserves_confirmed_stop_and_manager_verifies_restoration():
    live_reconcile = RECOVERY.split("double broker_stop=", 1)[1].split(
        "double broker_volume=", 1)[0]
    assert "p.current_stop=broker_stop" in live_reconcile
    assert "broker_stop_at_least_as_protective" in live_reconcile
    assert "else\n         {\n            staged_protection_repair_required=true;" in live_reconcile
    assert "g_position_protection_repair_required=" not in live_reconcile

    restore = MANAGER.split("bool PositionManagerRestoreMissingProtectiveStop(", 1)[1].split(
        "//--- Round a raw volume", 1)[0]
    assert "p.current_stop" in restore and "p.last_applied_stop" in restore and "p.initial_stop" in restore
    assert "available_distance<min_stop_dist" in restore
    assert "PositionManagerLatchStateFault" in restore
    assert "g_trade.PositionModify(ticket,recovery_stop,cur_tp)" in restore
    assert "PositionLookupByIdentifier(p.position_id,verified_ticket)" in restore
    assert restore.index("PositionLookupByIdentifier") < restore.index("g_positions[idx].current_stop=verified_stop")
    assert "if(!PositionSaveState(cfg))" in restore
    tick = MANAGER.split("void PositionManagerTick(", 1)[1]
    assert tick.index("PositionManagerRestoreMissingProtectiveStop") < tick.index("//--- Invalid TP check guard")


def test_recovery_mismatch_quarantines_entries_before_timer_or_tick_admission():
    on_init = (ROOT / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig").split(
        "int OnInit()", 1)[1].split("void OnDeinit()", 1)[0]
    repair_gate = on_init.index("if(g_position_protection_repair_required)")
    timer = on_init.index("EventSetTimer(5)")
    assert repair_gate < timer
    repair_handling = on_init[repair_gate:].split("if(ExecutionHasManagedWorkingOrder", 1)[0]
    assert "POSITION_STOP_RECOVERY" in repair_handling
    assert "PositionManagerLatchStateFault" not in repair_handling
    on_tick = (ROOT / "Experts" / "AMIGO.mq5").read_text(encoding="utf-8-sig").split("void OnTick()", 1)[1]
    on_tick = on_tick.split("int OnClosedBar(", 1)[0]
    assert "if(!PositionManagerAdmissionAllowed()) return;" in on_tick
    admission = MANAGER.split("bool PositionManagerAdmissionAllowed()", 1)[1].split("}", 1)[0]
    assert "!g_position_protection_repair_required" in admission
    clear = MANAGER.split("bool PositionManagerClearProtectionRepairIfComplete(const AmigoConfig &cfg)", 1)[1].split(
        "// A broker position without a server-side stop", 1)[0]
    assert "PositionLookupByIdentifier" in clear
    assert "g_position_protection_repair_required=false" in clear
    assert "All recovered positions have broker-confirmed protective stops" in clear
    assert "!MathIsValidNumber(required_stop)" in clear


def test_repair_gate_clears_only_after_all_stops_verify_and_never_clears_other_faults():
    assert not admission_after_repair(False, True, False)
    assert admission_after_repair(False, True, True)
    assert not admission_after_repair(True, True, True)
