"""Source integration checks only; no claim of native lifecycle execution."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[3]
def source(name):
    return (ROOT / 'MQL5' / name).read_text(encoding='utf-8-sig')


def test_decision_starts_with_explicit_unresolved_horizon():
    strategy = source('Include/Strategy Engine.mqh')
    contract = strategy.split('struct DecisionResult', 1)[1].split('};', 1)[0]
    assert re.search(r'ENUM_HORIZON\s+horizon;', contract)
    decide = strategy.split('DecisionResult Decide(', 1)[1]
    assert 'd.horizon    = (ENUM_HORIZON)0;' in decide
    assert decide.index('d.horizon') < decide.index('return d;')


def test_selected_horizon_reaches_geometry_and_intent():
    expert = source('Experts/AMIGO.mq5')
    body = expert.split('int OnClosedBar(', 1)[1].split('void OnTradeTransaction(', 1)[0]
    selection = body.index('dr.horizon=selected_horizon;')
    assert selection < body.index('if(dr.horizon == HORIZON_SCALPING) stop_tf')
    assert selection < body.index('ti.horizon          = dr.horizon;')
    assert body.index('ti.horizon          = dr.horizon;') < body.index('ValidateIntent(ti,')


def test_each_registration_uses_executed_intent_horizon():
    body = source('Experts/AMIGO.mq5').split('int OnClosedBar(', 1)[1].split('void OnTradeTransaction(', 1)[0]
    calls = re.findall(r'PositionManagerRegister\((.*?)\);', body, re.S)
    # Known partial execution, synthetic preflight, and confirmed full execution.
    assert len(calls) == 3
    assert all(re.search(r',\s*ti.horizon\s*$', call) for call in calls)
    assert 'ti.horizon!=HORIZON_SCALPING' in source('Include/Execution Engine.mqh')


def test_position_owned_horizon_is_persisted_and_restored():
    manager = source('Include/Position Manager.mqh')
    recovery = source('Include/PositionRecovery.mqh')
    assert 'g_positions[n].horizon               = horiz;' in manager
    assert 'ENUM_HORIZON horiz = g_positions[i].horizon;' in manager
    assert 'FileWriteInteger(handle, (int)g_positions[i].horizon, INT_VALUE);' in recovery
    assert 'p.horizon               = (ENUM_HORIZON)FileReadInteger(handle, INT_VALUE);' in recovery
    assert '(int)p.horizon<HORIZON_SCALPING || (int)p.horizon>HORIZON_SWING' in recovery
    assert 'actual.horizon!=expected.horizon' in recovery
