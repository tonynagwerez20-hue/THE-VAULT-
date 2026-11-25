"""Frozen prior-value acceptance predicates, not native history validation."""
from pathlib import Path
import re
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[3]
A=(ROOT/'MQL5/Include/Auction.mqh').read_text(encoding='utf-8-sig')
BODY=A.split('bool ClosedValueAcceptance(',1)[1].split('#endif',1)[0]
@pytest.mark.parametrize('closes,expected',[( [112,111],(True,False)),([89,88],(False,True)),([112,100],(False,False)),([110,111],(False,False)),([90,89],(False,False)),([100,100],(False,False))])
def test_two_closed_confirmations_strictly_beyond_frozen_value(closes,expected):
    env={'session_rates':[SimpleNamespace(close=c) for c in closes],'vah':110,'val':90}
    outputs=[]
    for name in ['above','below']:
        expr=re.search(name+r'=(session_rates.*?);',BODY).group(1)
        outputs.append(eval(expr.replace('&&','and'),{'__builtins__':{}},env))
    assert tuple(outputs)==expected

def test_value_reference_excludes_both_confirmation_bars_and_requires_history():
    assert 'count<7' in BODY
    assert 'prior[i-2]=session_rates[i]' in BODY
    assert 'for(int i=2;i<count;i++)' in BODY
    assert 'ComputeClosedSessionValue(prior,count-2' in BODY
    assert 'above=false; below=false;' in BODY
    assert 'session_rates[i-1].time<=session_rates[i].time' in BODY
    f=(ROOT/'MQL5/Include/FeatureVector.mqh').read_text(encoding='utf-8-sig')
    assert 'fs.acceptance_available=ClosedValueAcceptance(session_rates,session_count,bin,fs.acceptance_above,fs.acceptance_below);' in f
    assert 'fs.acceptance_above = false;' not in f
