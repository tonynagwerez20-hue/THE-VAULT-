"""Offline source-expression tests; no MQL runtime or performance claims."""
from pathlib import Path
from types import SimpleNamespace
import re
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/Strategy Engine.mqh').read_text(encoding='utf-8-sig')
F=(ROOT/'MQL5/Include/FeatureVector.mqh').read_text(encoding='utf-8-sig')
E=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')

@pytest.mark.parametrize('direction,sweep,expected',[(1,-1,True),(1,1,False),(-1,1,True),(-1,-1,False),(1,0,False),(-1,0,False)])
def test_rejection_must_match_trade_direction(direction,sweep,expected):
    expr=re.search(r'bool directional_rejection=(.*?);',S).group(1)
    assert eval(expr.replace('&&','and'),{'__builtins__':{}},{'f':SimpleNamespace(sweep_reject=True,last_sweep_dir=sweep),'dir':direction})==expected

@pytest.mark.parametrize('direction,fusion,enabled,expected',[(1,-.5,True,False),(-1,.5,True,False),(1,.5,True,True),(-1,-.5,True,True),(1,-.25,True,False),(-1,.25,True,False),(1,0,True,True),(1,-.8,False,True)])
def test_opposing_pressure_veto_from_actual_expression(direction,fusion,enabled,expected):
    expr=re.search(r'if\((cfg.tick_pressure_enabled &&.*?)\)\s*\{ reason="PROXY_PRESSURE_OPPOSES_ENTRY"',S).group(1)
    reject=eval(expr.replace('&&','and').replace('(double)',''),{'__builtins__':{}},{'cfg':SimpleNamespace(tick_pressure_enabled=enabled,pressure_threshold=.25),'decision':SimpleNamespace(direction=direction),'f':SimpleNamespace(fusion=fusion)})
    assert (not reject)==expected

def test_directional_divergence_is_assembled_and_consumed_without_raw_count_units():
    assert 'fs.feature_version = 2;' in F
    assert 'normalizedA[i]=histA[i]/(double)tc' in F
    assert 'double d1 = normalizedA[sh_idx2]' in F and 'double d1 = normalizedA[sl_idx2]' in F
    assert 'fs.divergence_bull=cfg.tick_pressure_enabled ? div_bull : 0.0;' in F
    assert 'fs.divergence_bear=cfg.tick_pressure_enabled ? div_bear : 0.0;' in F
    mr=S.split('double MR_Evidence(',1)[1].split('double ContinuationEvidence(',1)[0]
    assert '((dir==1) ? f.divergence_bull : f.divergence_bear)' in mr
    assert 'double div_score     = f.delta_divergence' not in mr

def test_real_entry_path_has_snapshot_horizon_and_proxy_contract_before_risk():
    gate=S.split('bool HorizonProxyAgreement(',1)[1].split('//--- Mean-reversion',1)[0]
    for token in ['decision.snapshot_id!=f.snapshot_id','f.decision_boundary!=boundary','f.closed_bar_time>=boundary','f.timeframe!=PERIOD_M1','f.timestamp!=f.closed_bar_time','f.symbol!=cfg.symbol','eligible!=decision.horizon']:assert token in gate
    b=E.split('int OnClosedBar(',1)[1]
    assert b.index('dr.horizon=selected_horizon;')<b.index('HorizonProxyAgreement(decision_feat,td,dr,rs.regime,g_cfg,decision_boundary,proxy_reason)')<b.index('RiskAllows(g_cfg, risk_reason)')
    assert 'decision_feat.divergence_bull = 0.0;' in b and 'decision_feat.divergence_bear = 0.0;' in b
    assert 'streaming_footprint=DIAGNOSTIC broker_depth=UNAVAILABLE' in b
