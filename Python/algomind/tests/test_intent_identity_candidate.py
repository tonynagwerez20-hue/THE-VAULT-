"""Intent wire-contract boundaries; source checks, not MQL runtime tests."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]

@pytest.mark.parametrize('now,created,expiry,expected',[(100,90,101,True),
    (100,90,100,False),(100,101,120,False),(0,0,60,False),
    (100,0,120,False),(100,90,90,False),(100,90,89,False)])
def test_intent_lifetime_is_positive_and_half_open(now,created,expiry,expected):
    assert (0<created<=now<expiry) is expected


def test_execution_validates_identity_symbol_and_clock_before_broker_access():
    s=(ROOT/'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig')
    validate=s.split('bool ValidateIntent(',1)[1].split('bool ExecutionDealMatchesIntent(',1)[0]
    for condition in ('ti.schema_version!=Amigo_SCHEMA_VERSION','ti.intent_id<=0',
        'ti.snapshot_id!=ti.intent_id','ti.symbol!=cfg.symbol','ti.symbol==""',
        'now<=0','ti.timestamp<=0','ti.timestamp>now','ti.expiry<=ti.timestamp',
        'ti.expiry <= now'):
        assert condition in validate
    execute=s.split('ExecutionResult ExecuteIntent(',1)[1]
    assert execute.index('ValidateIntent(ti,cfg,preflight_reason)')<execute.index('ExecutionVolumeValid(')


def test_shadow_fixture_has_valid_identity_and_explicit_horizons():
    s=(ROOT/'MQL5/Scripts/Test_ShadowHarness.mq5').read_text(encoding='utf-8-sig')
    assert 'g_cfg.symbol = _Symbol;' in s
    for i,h in enumerate(('SCALPING','INTRADAY','SWING')):
        assert f'test_intents[{i}].snapshot_id      = {9001+i};' in s
        assert f'test_intents[{i}].horizon          = HORIZON_{h};' in s
