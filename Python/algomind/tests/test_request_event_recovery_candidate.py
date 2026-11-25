"""Offline recovered-event consistency; native database behavior untested."""
from pathlib import Path
from types import SimpleNamespace as NS
import re
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/TransactionRecon.mqh').read_text(encoding='utf-8-sig')

def extracted_match(original,event,stage,outcome):
    body=S.split('bool ReconEventMatchesResponse(',1)[1].split('{',1)[1].split('}',1)[0]
    body=re.sub(r'//[^\n]*','',body)
    def supports(response,desired):
        return response.result.retcode==desired # independent classification stub
    scope=dict(original=original,event=event,stage=stage,outcome=outcome,ReconResponseSupportsOutcome=supports)
    for statement in body.split(';'):
        statement=' '.join(statement.split())
        if not statement: continue
        if statement=='return true': return True
        m=re.fullmatch(r'if\((.*)\) return false',statement)
        assert m,statement
        expr=re.sub(r'!(?!=)',' not ',m[1]).replace('&&',' and ').replace('||',' or ')
        if eval(expr.strip(),{'__builtins__':{}},scope): return False
    raise AssertionError('no result')

def response(request=7,order=20,deal=30,received=True,classification=4):
    return NS(send_ok=received,result=NS(request_id=request,order=order,deal=deal,retcode=classification))

@pytest.mark.parametrize('changes,stage,outcome,expected',[
 ({},1,0,True),({},2,4,True),({},0,0,False),({},3,4,False),
 ({'received':False},1,0,False),({'request':0},1,0,False),
 ({'request':8},1,0,False),({'order':21},1,0,False),
 ({'deal':31},1,0,False),({'classification':2},2,4,False),
 ({'classification':2},1,0,True), # evidence can evolve; no terminal authorization
])
def test_current_response_correlation(changes,stage,outcome,expected):
    assert extracted_match(response(),response(**changes),stage,outcome) is expected


def test_unknown_original_ids_can_gain_evidence_but_missing_request_cannot():
    assert extracted_match(response(order=0,deal=0),response(),1,0)
    assert not extracted_match(response(request=0),response(),1,0)


def test_startup_and_completion_load_checked_event_without_restoring_session_authority():
    loader=S.split('bool ReconLoadCurrentIntent()',1)[1].split('bool ReconJournalInit(',1)[0]
    assert 'ReconLoadRequestEvent(0,-1,0,empty)' in loader # orphan event blocks
    assert loader.index('!ReconLoadRequestEvent(intent,stage,outcome,decoded_response)')<loader.index('g_recon_recovered_present=true')
    event=S.split('bool ReconLoadRequestEvent(',1)[1].split('bool ReconLoadCurrentIntent()',1)[0]
    for token in ('event_intent>0','intent>0 && event_intent<=intent','ReconDecodeResponse(payload,decoded)','decoded.result.request_id>0','ERR_DATABASE_NO_MORE_DATA'):
        assert token in event
    assert 'g_recon_session_request=' not in event
    assert 'RiskRelease' not in event
    assert 'UPDATE ' not in event
