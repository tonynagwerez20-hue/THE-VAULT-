"""Independent recovery-policy oracle plus integration assertions, not MQL runtime."""
from pathlib import Path
import pytest

SOURCE = (Path(__file__).resolve().parents[3] / "MQL5/Include/Risk Engine.mqh").read_text()


def recover(slots):
    # Each slot: None (absent), "torn" (present but invalid), or generation.
    # Expected ledger history is B1, A2, B3, A4, ...; recovery must never
    # manufacture a missing committed generation or ignore damaged evidence.
    a, b = slots
    if "torn" in slots:
        return "BLOCKED"
    if a is None and b is None:
        return "BOOTSTRAP_POLICY_REQUIRED"
    if a is None:
        return 1 if b == 1 else "BLOCKED"
    if b is None or a % 2 != 0 or b % 2 != 1 or abs(a-b) != 1:
        return "BLOCKED"
    return max(a, b)


@pytest.mark.parametrize("slots,expected", [
    ((None,None),"BOOTSTRAP_POLICY_REQUIRED"), ((None,1),1),
    ((2,1),2), ((2,3),3), ((4,3),4),
    (("torn",3),"BLOCKED"), ((4,"torn"),"BLOCKED"),
    ((None,"torn"),"BLOCKED"), (("torn",None),"BLOCKED"),
    ((None,3),"BLOCKED"), ((4,None),"BLOCKED"),
    ((4,1),"BLOCKED"), ((2,5),"BLOCKED"),
    ((3,2),"BLOCKED"), ((2,2),"BLOCKED"),
])
def test_recovery_policy(slots, expected):
    assert recover(slots) == expected


def test_old_fallback_could_hide_consumed_opportunity():
    # A2 says previous bar rejected; B3 contained a new RESERVED outcome.
    # Corrupt B3: old max(valid slots) chooses A2 and can admit the bar again.
    valid_generations = [2]
    assert max(valid_generations) == 2
    assert recover((2,"torn")) == "BLOCKED"


@pytest.mark.parametrize("name,next_name,prefix", [
    ("RiskAccountRefresh", "RiskSymbolRefresh", "prefix"),
    ("RiskSymbolRefresh", "RiskPersistSymbol", "prefix"),
    ("RiskPersistAccount", "RiskPersist", "prefix"),
    ("RiskLegacyOpportunityStatus", "RiskLegacyAggregate", "prefixes[i]"),
    ("RiskLegacyAggregate", "RiskInitLocked", "prefixes[i]"),
])
def test_every_pair_consumer_guards_before_selecting_old_state(name,next_name,prefix):
    body=SOURCE.split(name+"(",1)[1].split(next_name+"(",1)[0]
    guard=body.index("RiskLedgerPairConsistent("+prefix)
    selection=body.index("(!vb ||")
    assert guard < selection


def test_init_checks_both_namespaces_before_bootstrap_or_selection():
    body=SOURCE.split("bool RiskInitLocked(",1)[1].split("bool RiskInit(",1)[0]
    for prefix in ("symbol_prefix,symbol_va", "account_prefix,account_va"):
        assert body.index("RiskLedgerPairConsistent("+prefix) < body.index("if(account_ledger_found)")


def test_pair_guard_checks_damage_identity_generation_and_initial_state():
    body=SOURCE.split("bool RiskLedgerPairConsistent(",1)[1].split("bool RiskLedgerSlotWrite(",1)[0]
    assert '"X","XG"' in body
    assert "if(present && !valid) return false;" in body
    assert "RiskAccountSlotIdentityValid(prefix,slots[slot],generation)" in body
    assert "a.generation%2!=0" in body and "b.generation%2!=1" in body
    assert "a.generation-b.generation" in body
    assert "if(vb) return b.generation==1;" in body
