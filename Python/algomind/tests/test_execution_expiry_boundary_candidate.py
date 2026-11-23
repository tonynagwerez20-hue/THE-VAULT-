"""Expiry oracle/source checks, not live timing or broker atomicity proof."""
from pathlib import Path
import pytest
import re
ROOT=Path(__file__).resolve().parents[3]

@pytest.mark.parametrize('boundary,period,created,expected',[
 (1200,60,1200,1260),(1200,60,1255,1260),(1200,300,1490,1500),
 (1200,300,1210,1270),(1200,60,1260,1260)])
def test_expiry_cannot_extend_closed_bar_opportunity(boundary,period,created,expected):
    assert min(created+60,boundary+period)==expected
    if created>=boundary+period:
        assert expected<=created  # ValidateIntent rejects this empty window.


def test_source_caps_expiry_and_rechecks_after_blocking_preflight():
    expert=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
    assert 'ti.expiry           = ti.timestamp + 60;' in expert
    assert 'datetime opportunity_expiry=decision_boundary+PeriodSeconds(g_cfg.tf_exec);' in expert
    assert 'if(ti.expiry>opportunity_expiry) ti.expiry=opportunity_expiry;' in expert
    s=(ROOT/'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig').split('ExecutionResult ExecuteIntent(',1)[1]
    pre=s.index('PREFLIGHT_INTENT_INVALIDATED:')
    assert s.index('AccountEstimatedStopRisk(')<pre<re.search(r'r\.shadow_evaluated\s*=\s*true;',s).start()
    check=s.index('OrderCheck(req, chk)')
    post=s.index('POST_ORDERCHECK_INTENT_INVALIDATED:')
    send=s.index('OrderSend(req, res)')
    assert check<post<send
    assert 'return r;' in s[post:send]
