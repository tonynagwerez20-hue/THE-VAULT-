"""Independent footprint examples and source integration; NOT native parity."""
from pathlib import Path
from collections import defaultdict
import math
import pytest
ROOT=Path(__file__).resolve().parents[3]/'MQL5'
H=(ROOT/'Include/FrozenFootprint.mqh').read_text(encoding='utf-8-sig')
F=(ROOT/'Include/FeatureVector.mqh').read_text(encoding='utf-8-sig')
O=(ROOT/'Include/Orderflow.mqh').read_text(encoding='utf-8-sig')
S=(ROOT/'Include/Strategy Engine.mqh').read_text(encoding='utf-8-sig')
def oracle(prices,width=1):
    if not math.isfinite(width) or width<=0 or len(prices)<2 or len(prices)>8192:return None
    bins=defaultdict(lambda:[0,0]);previous=None
    for price in prices:
        if not math.isfinite(price) or price<=0:return None
        key=math.floor(price/width)
        if key>9007199254740991:return None
        direction=0 if previous is None else (price>previous)-(price<previous)
        bins[key][0]+=1;bins[key][1]+=direction;previous=price
        if len(bins)>256:return None
    poc=min(bins,key=lambda k:(-bins[k][0],k))
    net=sum(v[1] for v in bins.values());den=sum(abs(v[1]) for v in bins.values())
    return net/den if den else 0,(poc+.5)*width,bins[poc][0]/len(prices)

@pytest.mark.parametrize('prices,expected',[
 ([10,11,12],(1,10.5,1/3)),([12,11,10],(-1,10.5,1/3)),
 ([10,10,10],(0,10.5,1)),([10,11,10],(0,10.5,2/3)),
 ([10,10,11],(1,10.5,2/3))])
def test_independent_footprint_examples(prices,expected):assert oracle(prices)==expected

@pytest.mark.parametrize('prices,width', [([],1),([10],1),([10,0],1),([10,float('nan')],1),([10,11],0),([10,11],float('inf')),(list(range(1,258)),1),([10]*8193,1)])
def test_invalid_and_overflow_examples(prices,width):assert oracle(prices,width) is None

def test_exact_bin_limit_and_repeatability():
    values=list(range(1,257))
    assert oracle(values) is not None
    assert oracle(values)==oracle(values)

def test_source_arithmetic_bounds_and_failure_latch_match_specification():
    for token in ['AM_FOOTPRINT_MAX_BINS 256','f.observations>=8192','if(f.failed) return false','f.failed=true;','f.failed=false;','f.count>=AM_FOOTPRINT_MAX_BINS','ZeroMemory(f)','net!=f.up-f.down','f.keys[i]<f.keys[peak]','(double)net/(double)absolute','(double)f.activity[peak]/(double)total']:assert token in H
    assert 'if(f.failed ||' in H
    assert 'ArrayResize' not in H

def test_same_reader_transaction_and_local_closed_event_replay():
    b=O.split('bool TryComputeDeltaA(',1)[1].split('// Compatibility caller',1)[0]
    assert b.count('CopyTicksRange(')==1
    assert 'FrozenFootprintReset(footprint,bin_width)' in b
    assert 'FrozenFootprintAdd(footprint,previous)' in b and 'FrozenFootprintAdd(footprint,price)' in b
    assert b.index('FrozenFootprintFinish(footprint)')<b.index('out=sum;')
    for token in ['CAM_FlowEvents frozen_events(2);','for(int e=19;e>=0;e--)','frozen_events.AddBar(r[e].time','fs.footprint_persistent=frozen_events.IsPersistent()','fs.footprint_divergence_bull=frozen_events.IsBullishDivergence()','fs.footprint_divergence_bear=frozen_events.IsBearishDivergence()']:assert token in F
    assert 'g_events_engine' not in F
    assert F.index('fs.footprint_available=false;')<F.index('if(cfg.tick_pressure_enabled)')

def test_footprint_is_consistency_gate_not_extra_score_and_keeps_horizon_rules():
    gate=S.split('bool HorizonProxyAgreement(',1)[1].split('//--- Mean-reversion',1)[0]
    for token in ['FROZEN_FOOTPRINT_UNAVAILABLE','FROZEN_FOOTPRINT_OPPOSES_ENTRY','FOOTPRINT_DIVERGENCE_AGAINST_CONTINUATION','FOOTPRINT_CONTINUATION_NOT_PERSISTENT','decision.horizon!=HORIZON_SCALPING']:assert token in gate
    scores=S.split('double MR_Evidence(',1)[1]
    assert 'footprint_' not in scores
