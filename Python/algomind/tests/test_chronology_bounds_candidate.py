"""Independent array-domain oracles and source checks; native not executed."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/Structure Engine.mqh').read_text(encoding='utf-8-sig')
C=(ROOT/'MQL5/Include/Chronology Validation.mqh').read_text(encoding='utf-8-sig')


@pytest.mark.parametrize('size,k,shift,expected', [(0,2,2,False),(5,2,2,True),
    (5,2,1,False),(5,2,3,False),(5,0,2,False),(5,-1,2,False),
    (5,2,2147483647,False),(5,2147483647,2,False)])
def test_swing_window_requires_every_neighbor_inside_array(size,k,shift,expected):
    # Independently stated domain: nonempty positive-width neighborhood, center
    # and every left/right neighbor in array. Python integers do not overflow.
    valid = k>0 and shift-k>=0 and shift+k<size
    assert valid is expected


def test_both_native_swing_helpers_guard_before_first_index():
    for name,next_name in [('IsConfirmedSwingHigh','IsConfirmedSwingLow'),
                           ('IsConfirmedSwingLow','FindLatestConfirmedSwing')]:
        body=S.split('bool '+name+'(',1)[1].split('bool '+next_name+'(',1)[0]
        guard='if(k<=0 || k>=size || shift<k || shift>=size-k) return false;'
        assert body.index(guard)<body.index('r[shift]')
    find=S.split('bool FindLatestConfirmedSwing(',1)[1].split('struct StructureState',1)[0]
    for guard in ('total>ArraySize(r)','k>(total-1)/2','!ArrayGetAsSeries(r)'):
        assert find.index(guard)<find.index('for(int i = k;')
    assert 'price_out=0.0;' in find and 'time_out=0;' in find


@pytest.mark.parametrize('count,size,minimum,maximum,expected', [
    (0,0,0,4,False),(0,0,1,4,False),(3,3,-1,4,False),
    (3,3,4,3,False),(3,4,1,4,False),(3,3,3,4,True)])
def test_count_contract(count,size,minimum,maximum,expected):
    assert (minimum>0 and maximum>=minimum and minimum<=count<=maximum and count==size) is expected


def test_native_validator_rejects_bad_contract_before_first_bar_access():
    for guard in ('minimum_count<=0','maximum_count<minimum_count','count<=0'):
        assert C.index(guard)<C.index('bars[0].time')
