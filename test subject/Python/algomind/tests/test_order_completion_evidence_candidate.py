"""Order-completion predicate fixtures from current MQL source, not native history."""
from pathlib import Path
from types import SimpleNamespace as NS
import math
import re
import pytest
SOURCE=(Path(__file__).resolve().parents[3]/'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig')
BODY=SOURCE.split('bool ExecutionCompletedOrderMatches(',1)[1].split('// Aggregate only',1)[0]

def accepted(**changes):
    scope=dict(magic=7,type=0,state=4,position_id=12,position=12,filling=0,symbol='XAUUSD',setup=100,done=101,
               initial=.02,remaining=0.,tolerance=1e-8,request=NS(magic=7,type=0,type_filling=0,volume=.02),
               ti=NS(symbol='XAUUSD',timestamp=100),ORDER_STATE_FILLED=4,MathIsValidNumber=math.isfinite,MathAbs=abs)
    scope.update(changes)
    for first in ('if(magic!=','if(!MathIsValidNumber(initial)'):
        condition=BODY[BODY.index(first)+3:].split(')\n',1)[0]
        condition=re.sub(r'\((?:long|ulong)\)','',condition)
        condition=re.sub(r'!(?!=)',' not ',condition).replace('||',' or ').replace('&&',' and ')
        if eval(' '.join(condition.split()),{'__builtins__':{}},scope): return False
    return True

@pytest.mark.parametrize('change',[
 {'magic':8},{'type':1},{'state':3},{'position_id':0},{'position_id':13},{'filling':1},
 {'symbol':'EURUSD'},{'setup':99},{'done':99},{'initial':.01},{'initial':float('nan')},
 {'initial':float('inf')},{'remaining':.001},{'remaining':-.001},{'remaining':float('nan')},
])
def test_independent_conflicts_do_not_confirm_full_order(change):
    assert not accepted(**change)


def test_matching_terminal_order_and_small_representation_noise():
    assert accepted()
    assert accepted(initial=.020000000001)


def test_real_fill_path_checks_order_after_deals_without_discarding_known_fill():
    fill=SOURCE.split('string aggregate_reason="";',1)[1].split('ORDERSEND_DEFINITIVE_REJECTION',1)[0]
    assert fill.index('ExecutionAggregateOrderDeals(')<fill.index('ExecutionCompletedOrderMatches(')<fill.index('FILL_CONFIRMED')
    failed=fill.split('if(!ExecutionCompletedOrderMatches(',1)[1].split('else r.comment="FILL_CONFIRMED"',1)[0]
    assert 'r.outcome_uncertain=true' in failed
    assert 'r.accepted=false' not in failed
    assert 'HistoryOrderSelect(order)' in BODY
    assert not re.search(r'HistoryOrderGet(?:Integer|Double|String)\(order,ORDER_\w+\)',BODY)
