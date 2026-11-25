"""Offline recovery-volume contract checks; no MQL runtime is exercised."""
from pathlib import Path
import math


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "MQL5" / "Include" / "PositionRecovery.mqh").is_file()
)
RECOVERY = (ROOT / "MQL5" / "Include" / "PositionRecovery.mqh").read_text(
    encoding="utf-8-sig"
)


def volume_reconciles(persisted: float, observed: float, step: float) -> bool:
    """Independent contract oracle: only same-volume state is recoverable."""
    return (
        math.isfinite(persisted)
        and persisted > 0.0
        and math.isfinite(observed)
        and observed > 0.0
        and math.isfinite(step)
        and step > 0.0
        and abs(observed - persisted) <= step * 0.25
    )


def serialized_record_matches(expected: dict, serialized: dict, stored_checksum: int,
                              serialized_checksum: int, expected_checksum: int) -> bool:
    """Independent payload oracle; a valid trailer cannot mask a bad field."""
    return (serialized == expected and stored_checksum == serialized_checksum
            and stored_checksum == expected_checksum)


def test_recovered_trailing_policy_must_be_implemented_and_have_valid_parameters():
    # Recovered mode belongs to the saved position, not the current input mode.
    # OFF/dynamic need no ATR inputs; ATR requires both finite positive values.
    def allowed(saved_mode, multiplier, activation):
        return saved_mode in (0, 1, 2) and (
            saved_mode != 2 or all(math.isfinite(x) and x > 0
                                   for x in (multiplier, activation)))

    for mode in (0, 1, 2):
        assert allowed(mode, 1.5, 1.0)
    for mode in (-1, 3, 4, 99):
        assert not allowed(mode, 1.5, 1.0)
    for invalid in (0, -1, float('nan'), float('inf')):
        assert not allowed(2, invalid, 1.0)
        assert not allowed(2, 1.5, invalid)
    assert allowed(1, 0, 0)

    validation = RECOVERY.split('if(p.position_id==0', 1)[1].split(
        'saved_record_checksum!=PositionStateRecordChecksum(p)', 1)[0]
    for condition in (
        'p.trailing_mode!=TRAIL_OFF',
        'p.trailing_mode!=TRAIL_DYNAMIC_25_PERCENT',
        'p.trailing_mode!=TRAIL_ATR',
        'p.trailing_mode==TRAIL_ATR',
        '!MathIsValidNumber(p.trail_atr_mult)',
        'p.trail_atr_mult<=0.0',
        '!MathIsValidNumber(p.trail_activate_r)',
        'p.trail_activate_r<=0.0',
    ):
        assert condition in validation
    assert 'return -1;' in validation


def test_recovery_rejects_inconsistent_initial_risk_geometry():
    # Expected distance is derived from the independently specified entry and
    # original stop, regardless of whether a stored checksum is internally valid.
    def valid(direction, entry, initial_stop, stored_risk):
        if not all(math.isfinite(x) and x > 0 for x in (entry, initial_stop, stored_risk)):
            return False
        side_ok = (direction == 1 and initial_stop < entry) or (
            direction == -1 and initial_stop > entry)
        distance = abs(entry - initial_stop)
        return side_ok and distance > 0 and abs(stored_risk - distance) <= max(1, distance) * 1e-10

    assert valid(1, 2000, 1990, 10)
    assert valid(-1, 2000, 2010, 10)
    assert not valid(1, 2000, 2010, 10)
    assert not valid(-1, 2000, 1990, 10)
    assert not valid(1, 2000, 2000, 10)
    assert not valid(1, 2000, 1990, 1)  # would trigger partial/trailing at 1/10th R
    assert not valid(1, 2000, 1990, float('nan'))
    validation = RECOVERY.split('double initial_distance=', 1)[1].split(
        'for(int prior=0;', 1)[0]
    assert 'MathAbs(p.entry-p.initial_stop)' in validation
    assert '!initial_geometry_valid' in validation
    assert 'MathAbs(p.initial_risk_per_unit-initial_distance)' in validation
    assert 'return -1;' in validation


def test_recovery_checks_broker_direction_before_adopting_protective_stop():
    verification = RECOVERY.split('// Invariant Check: Broker Position Verification', 1)[1]
    assert verification.index('PositionGetInteger(POSITION_TYPE)') < verification.index(
        'double broker_stop=PositionGetDouble(POSITION_SL)')
    assert '(p.direction==+1 && pos_side==POSITION_TYPE_BUY)' in verification
    assert '(p.direction==-1 && pos_side==POSITION_TYPE_SELL)' in verification
    assert 'pos_mag != cfg.magic_number || !side_matches' in verification


def test_failed_or_reentered_recovery_preserves_existing_protection_gate():
    # Accepted gate must survive either re-entry rejection or a failure after
    # a staged missing-stop observation. Only a complete recovery commits it.
    def result(prior, records, succeeds, reentry=False):
        if reentry or not succeeds:
            return prior
        return any(records)

    assert result(True, [], False, reentry=True) is True
    assert result(False, [True], False) is False
    assert result(True, [False], False) is True
    assert result(False, [False, True], True) is True
    assert result(True, [], True) is False

    loader = RECOVERY.split('int PositionReconcileState(', 1)[1]
    assert 'bool staged_protection_repair_required=false;' in loader
    assignment = 'g_position_protection_repair_required=staged_protection_repair_required;'
    assert loader.count('g_position_protection_repair_required=') == 2
    assert loader.count(assignment) == 2
    assert loader.index('if(ArraySize(g_positions)!=0)') < loader.index(assignment)
    assert assignment + '\n      return 0;' in loader  # fully validated empty startup
    assert loader.rindex(assignment) > loader.index('g_positions[i]=staged_positions[i];')


def test_recovery_rejects_unexplained_broker_volume_change_before_adopting_it():
    start = RECOVERY.index("double broker_volume=PositionGetDouble(POSITION_VOLUME);")
    end = RECOVERY.index("double cur_tp", start)
    block = RECOVERY[start:end]

    assert "MathAbs(broker_volume-p.current_volume)>volume_step*0.25" in block
    assert block.index("MathAbs(broker_volume-p.current_volume)>volume_step*0.25") < block.index(
        "p.current_volume=broker_volume;"
    )
    assert "outcome is ambiguous and recovery is blocked" in block
    assert "return -1;" in block

    # Independently derived expected outcomes: a saved partial state whose
    # broker remainder matches is recoverable; any unexplained reduction or
    # increase beyond tolerance, or invalid metadata, must be rejected.
    assert volume_reconciles(0.70, 0.70, 0.10)
    assert volume_reconciles(0.70, 0.7000001, 0.10)
    assert not volume_reconciles(1.00, 0.70, 0.10)
    assert not volume_reconciles(0.70, 0.80, 0.10)
    assert not volume_reconciles(0.70, 0.70, 0.0)
    assert not volume_reconciles(0.70, float("nan"), 0.10)


def test_save_readback_compares_serialized_payload_not_only_checksum_trailer():
    helper = RECOVERY.split("bool PositionStateFileRecordMatchesExpected(", 1)[1].split(
        "long PositionStateIdentityHash", 1
    )[0]
    for field in (
        "actual.position_id!=expected.position_id", "actual.direction!=expected.direction",
        "actual.entry!=expected.entry", "actual.initial_stop!=expected.initial_stop",
        "actual.initial_target!=expected.initial_target", "actual.initial_atr!=expected.initial_atr",
        "actual.current_stop!=expected.current_stop", "actual.partial_done!=expected.partial_done",
        "actual.be_activated!=expected.be_activated", "actual.initial_volume!=expected.initial_volume",
        "actual.current_volume!=expected.current_volume",
    ):
        assert field in helper
    assert "stored_checksum!=PositionStateRecordChecksum(actual)" in helper
    assert "stored_checksum!=PositionStateRecordChecksum(expected)" in helper
    assert RECOVERY.count("PositionStateFileRecordMatchesExpected(verify,g_positions[i])") == 1
    assert RECOVERY.count("PositionStateFileRecordMatchesExpected(primary_handle,g_positions[i])") == 1
    assert "FileTell(verify)!=expected_size" in RECOVERY
    assert "FileTell(primary_handle)!=expected_size" in RECOVERY

    expected = {"id": 8, "direction": 1, "entry": 2000.0,
                "stop": 1990.0, "volume": 0.1}
    checksum = 12345
    assert serialized_record_matches(expected, dict(expected), checksum, checksum, checksum)
    corrupt_field = dict(expected, stop=1989.0)
    # The trailer remains unchanged, but direct payload comparison rejects it.
    assert not serialized_record_matches(expected, corrupt_field, checksum, checksum, checksum)
    assert not serialized_record_matches(expected, dict(expected), checksum, checksum + 1, checksum)


if __name__ == "__main__":
    test_recovery_rejects_unexplained_broker_volume_change_before_adopting_it()
