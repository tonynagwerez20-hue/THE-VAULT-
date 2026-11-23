"""Independent arithmetic boundary evidence and source ordering; no native parity."""
import math
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]

@pytest.mark.parametrize('equity,pct,valid',[(1000.,1.,True),(16.15,.5,True),(0.,1.,False),
 (float('nan'),1.,False),(float('inf'),1.,False),(1e-320,1e-100,False)])
def test_independently_derived_budget_domain(equity,pct,valid):
    budget=equity*(pct/100.)
    assert (math.isfinite(budget) and budget>0)==valid

def test_positive_factors_can_underflow_before_distortion_division():
    equity,pct=1e-320,1e-100
    assert equity>0 and pct>0
    budget=equity*(pct/100.)
    assert budget==0
    with pytest.raises(ZeroDivisionError): _=1./budget

def test_production_request_validates_denominator_before_division():
    src=(ROOT/'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig')
    start=src.index('double request_target_risk=')
    divide=src.index('double request_risk_distortion=',start)
    block=src[start:divide]
    assert 'request_target_risk<=0.0' in block
    assert 'FINAL_REQUEST_TARGET_RISK_INVALID' in block
    assert 'r.risk_guard_blocked=true;' in block and 'return r;' in block

def test_production_sizing_validates_derived_values_before_rounding():
    src=(ROOT/'MQL5/Include/Account Execution Engine.mqh').read_text(encoding='utf-8-sig')
    start=src.index('env.target_risk_amount =')
    divide=src.index('env.raw_volume =',start)
    assert 'TARGET_RISK_AMOUNT_INVALID' in src[start:divide]
    assert '!MathIsValidNumber(env.risk_per_lot)' in src[start:divide]
    branch=src.index('//--- 3-State Evaluation',divide)
    assert 'RAW_VOLUME_INVALID' in src[divide:branch]
    assert '#define AMIGO_MAX_ESTIMATED_STOP_LOSS_PERCENT 2.0' in src
