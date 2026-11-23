"""Offline contracts/reference scenarios, not native tick-history evidence."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import re
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/Strategy Engine.mqh').read_text(encoding='utf-8-sig')
F=(ROOT/'MQL5/Include/FeatureVector.mqh').read_text(encoding='utf-8-sig')
O=(ROOT/'MQL5/Include/Orderflow.mqh').read_text(encoding='utf-8-sig')

def mr_gate(direction,fusion,rejection):
    body=S.split('double MR_Evidence(',1)[1].split('double ContinuationEvidence(',1)[0]
    expression=re.search(r'if\((!directional_rejection.*?)\) return 0.0;',body).group(1)
    expression=expression.replace('(double)','').replace('&&',' and ').replace('!','not ')
    return not eval(expression,{'__builtins__':{}},{'dir':direction,'directional_rejection':rejection,'f':SimpleNamespace(fusion=fusion,sweep_reject=rejection)})

@pytest.mark.parametrize('direction',[-1,1])
@pytest.mark.parametrize('aligned,rejection,expected',[(0,False,False),(-.8,False,False),(.099,False,False),(.1,False,True),(.8,False,True),(0,True,True)])
def test_mr_directional_pressure_and_disabled_fallback(direction,aligned,rejection,expected):
    assert mr_gate(direction,direction*aligned,rejection)==expected

def test_price_basis_is_explicit_frozen_and_rechecked():
    body=O.split('bool TryComputeDeltaA(',1)[1].split('//--- Proxy B',1)[0]
    assert 'bid_basis ? ticks[0].bid : ticks[0].last' in body
    assert 'bid_basis ? ticks[i].bid : ticks[i].last' in body
    assert 'bid_basis ? TICK_FLAG_BID : TICK_FLAG_LAST' in body
    assert 'chart_mode!=SYMBOL_CHART_MODE_BID && chart_mode!=SYMBOL_CHART_MODE_LAST' in body
    assert 'observed_price_activity' in body
    assert 'ticks[i].time_msc>=end_ms' in body and 'got>=AM_MAX_PROXY_TICKS' in body
    assert 'TryComputeDeltaA(symbol,r[i].time,tick_end,histA[i],tc,window_footprint,bin,proxy_chart_mode)' in F
    assert F.index('long proxy_chart_mode=-1;')<F.index('TryComputeDeltaA(')<F.index('final_chart_mode!=proxy_chart_mode')<F.index('fs.fusion = ComputeFusion')

def test_both_strategies_receive_same_validated_proxy_before_horizon_selection():
    e=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
    b=e.split('int OnClosedBar(',1)[1]
    assert b.index('if(!g_cfg.tick_pressure_enabled)')<b.index('ScoreStrategies(decision_feat, g_ext, g_cfg)')<b.index('SelectApprovedHorizon(')
    for call in ['ContinuationEvidence(f, +1)','ContinuationEvidence(f, -1)','MR_Evidence(f, +1)','MR_Evidence(f, -1)']:assert call in S
    assert 'double dir_fusion = (double)dir * f.fusion;' in S

@pytest.mark.parametrize('vector,strategy,horizon',[
 ((1,1,1,1,1,1,1),'CONT','SWING'),
 ((0,0,1,1,1,1,1),'CONT','INTRADAY'),
 ((0,0,0,0,0,1,1),'CONT','SCALPING'),
 ((0,0,0,0,0,0,1),'MR','INTRADAY'),
 ((0,0,1,0,0,0,1),'MR','SCALPING')])
def test_proxy_supported_signal_retains_approved_horizon(vector,strategy,horizon):
    path=Path(__file__).with_name('test_approved_horizon_selector_candidate.py')
    spec=importlib.util.spec_from_file_location('approved_horizon',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    for direction in (-1,1):
        assert mr_gate(direction,.4*direction,False)
        assert mod.source_expressions(tuple(v*direction for v in vector),direction,strategy)==horizon
