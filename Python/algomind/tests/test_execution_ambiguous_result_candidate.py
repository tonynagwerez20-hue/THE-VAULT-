"""Independent uncertain-result policy plus source wiring; no broker calls."""
from pathlib import Path
import math
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig')

def clean_refusal(explicit_refusal,order,deal,volume,external):
    return explicit_refusal and order==0 and deal==0 and math.isfinite(volume) and volume==0 and external==0

@pytest.mark.parametrize('order,deal,volume,external',[(1,0,0,0),(0,1,0,0),
    (0,0,.01,0),(0,0,-.01,0),(0,0,float('nan'),0),(0,0,0,9)])
def test_refusal_with_conflicting_evidence_remains_uncertain(order,deal,volume,external):
    assert not clean_refusal(True,order,deal,volume,external)


def test_only_uncontradicted_explicit_refusal_is_clear():
    assert clean_refusal(True,0,0,0,0)
    assert not clean_refusal(False,0,0,0,0)


def test_failed_api_result_preserves_identifiers_without_claiming_fill():
    failure=S.split('if(!send_ok)',1)[1].split('r.retcode      = res.retcode',1)[0]
    assert failure.index('r.order_ticket=res.order;')<failure.index('return r;')
    assert failure.index('r.deal_ticket=res.deal;')<failure.index('return r;')
    assert 'res.request_id,res.retcode_external,res.comment' in failure
    assert 'r.outcome_uncertain = true;' in failure
    assert 'r.accepted = true' not in failure


def test_actual_rejection_gate_checks_conflicting_fields():
    gate=S.split('bool clean_rejection=',1)[1].split('if(clean_rejection)',1)[0]
    for token in ('ExecutionRetcodeIsDefinitiveRejection(res.retcode)', 'res.order==0',
                  'res.deal==0','MathIsValidNumber(res.volume)','res.volume==0.0',
                  'res.retcode_external==0'):
        assert token in gate
    branch=S.split('if(clean_rejection)',1)[1]
    assert 'r.outcome_uncertain=true;' in branch
