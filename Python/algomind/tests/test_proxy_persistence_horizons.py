"""Independent examples plus current-source predicates; not native parity."""
from pathlib import Path
from types import SimpleNamespace
import math,re
import pytest
ROOT=Path(__file__).resolve().parents[3]/'MQL5/Include'
O=(ROOT/'Orderflow.mqh').read_text(encoding='utf-8-sig')
S=(ROOT/'Strategy Engine.mqh').read_text(encoding='utf-8-sig')
F=(ROOT/'FeatureVector.mqh').read_text(encoding='utf-8-sig')

@pytest.mark.parametrize('value,prior,expected',[(0,list(range(1,21)),0),(21,list(range(1,21)),100),(5,[5]*20,50),(10,[5]*10+[15]*10,50)])
def test_percentile_expected_extremes_and_ties(value,prior,expected):
    # Independent count definition; evaluate current production final expression.
    expression=re.search(r'rank=(100\.0.*?);',O).group(1).replace('(double)','')
    env={'below':sum(x<value for x in prior),'equal':sum(x==value for x in prior),'n':len(prior)}
    assert eval(expression,{'__builtins__':{}},env)==expected

@pytest.mark.parametrize('values,direction,expected',[([.4,.2,-.1],1,2),([-.4,-.2,.1],-1,2),([.4,0,.5],1,1),([-.4,.3],1,0),([.4,.3,.2],1,3),([0,0],1,0)])
def test_persistence_stops_at_first_neutral_or_opposing_bar(values,direction,expected):
    body=O.split('int ProxyDirectionalPersistence(',1)[1].split('//--- Rolling',1)[0]
    condition=re.search(r'if\(\(double\)(.*?)\) break;',body).group(1)
    count=0
    for i in range(len(values)):
        if eval(condition,{'__builtins__':{}},{'direction':direction,'normalized':values,'i':i}):break
        count+=1
    assert count==expected

@pytest.mark.parametrize('horizon,hypothesis,persistence,state,enabled,reject',[
 (1,1,1,1,True,False),(2,1,1,1,True,True),(3,1,1,1,True,True),
 (2,1,2,1,True,False),(3,1,2,1,True,False),(3,1,5,-1,True,True),
 (2,2,0,0,True,False),(3,1,0,0,False,False)])
def test_horizon_confirmation_uses_actual_gate(horizon,hypothesis,persistence,state,enabled,reject):
    expression=re.search(r'if\((cfg.tick_pressure_enabled && decision.hypothesis==HYP_CONTINUATION.*?)\)\s*\{ reason="PROXY_CONTINUATION_NOT_PERSISTENT"',S.split('// M1 persistence supports entry timing only',1)[1],re.S).group(1)
    expression=' '.join(expression.replace('&&','and').replace('||','or').split())
    env={'cfg':SimpleNamespace(tick_pressure_enabled=enabled),'decision':SimpleNamespace(hypothesis=hypothesis,horizon=horizon,direction=1),'f':SimpleNamespace(pressure_state=state,persistence=persistence),'HYP_CONTINUATION':1,'HORIZON_SCALPING':1}
    assert eval(expression,{'__builtins__':{}},env)==reject

def test_actual_assembly_uses_frozen_inputs_and_no_placeholders():
    assert 'prior_ranges[p]=r[p+1].high-r[p+1].low' in F
    assert 'ProxyPriorPercentile(current_range,prior_ranges,fs.vol_percentile)' in F
    assert 'ProxyDirectionalPersistence(normalizedA,fs.pressure_state)' in F
    assert 'fs.vol_percentile = 50.0;' not in F
    assert 'fs.persistence = 0;' not in F
    assert 'tick_end-r[i].time!=nominal_seconds' in F
