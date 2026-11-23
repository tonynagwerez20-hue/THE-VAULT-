"""Recovery geometry expectations; no terminal or persistence runtime exercised."""
from pathlib import Path
import math
import pytest
ROOT=Path(__file__).resolve().parents[3]

@pytest.mark.parametrize('direction,entry,target,trigger,valid',[
 (1,100,120,106.6,True),(-1,100,80,88,True),
 (1,100,120,0,False),(1,100,90,105,False),(-1,100,110,95,False),
 (1,100,120,100,False),(1,100,120,120,False),
 (-1,100,80,100,False),(-1,100,80,80,False),
 (1,100,120,float('nan'),False)])
def test_saved_break_even_must_lie_strictly_on_profit_path(direction,entry,target,trigger,valid):
    result=(all(math.isfinite(x) and x>0 for x in (entry,target,trigger)) and
            ((direction==1 and entry<trigger<target) or
             (direction==-1 and target<trigger<entry)))
    assert result is valid


def test_native_recovery_checks_before_commit_without_recomputing_trigger():
    s=(ROOT/'MQL5/Include/PositionRecovery.mqh').read_text(encoding='utf-8-sig')
    for token in ('p.initial_target>p.entry','p.be_trigger_price>p.entry',
                  'p.be_trigger_price<p.initial_target','p.initial_target<p.entry',
                  'p.be_trigger_price<p.entry','p.be_trigger_price>p.initial_target',
                  '!management_geometry_valid'):
        assert token in s
    check=s.index('!management_geometry_valid')
    reject=s.index('return -1;',check)
    commit=s.index('g_positions[i]=staged_positions[i]')
    assert check<reject<commit


def test_registration_enforces_same_trigger_domain_before_allocation():
    s=(ROOT/'MQL5/Include/Position Manager.mqh').read_text(encoding='utf-8-sig')
    body=s.split('void PositionManagerRegister(',1)[1]
    for token in ('be_trigger<=entry || be_trigger>=target',
                  'be_trigger>=entry || be_trigger<=target'):
        assert body.index(token)<body.index('ArrayResize(g_positions, n + 1)')
