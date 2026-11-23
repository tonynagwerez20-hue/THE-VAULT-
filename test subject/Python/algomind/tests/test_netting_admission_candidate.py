"""Netting admission table and source checks, not broker-race verification."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig')

@pytest.mark.parametrize('mode,position,order,own,allowed',[
 ('netting',True,False,False,False),('exchange',False,True,False,False),
 ('netting',False,False,False,True),('hedging',True,False,False,True),
 ('hedging',False,True,True,False),('hedging',False,True,False,True),
 ('unknown',False,False,False,False)])
def test_independent_symbol_admission_table(mode,position,order,own,allowed):
    actual=(mode in {'netting','exchange','hedging'} and
            not (mode!='hedging' and position) and
            not (order and (mode!='hedging' or own)))
    assert actual is allowed


def test_shared_execution_path_checks_account_model_before_submission():
    helper=S.split('bool ExecutionSymbolAdmissionAllows(',1)[1].split('// Best-effort containment',1)[0]
    for token in ('ACCOUNT_MARGIN_MODE_RETAIL_HEDGING','ACCOUNT_MARGIN_MODE_RETAIL_NETTING',
                  'ACCOUNT_MARGIN_MODE_EXCHANGE','NETTING_SYMBOL_POSITION_EXISTS',
                  'SYMBOL_WORKING_ORDER_UNRESOLVED','PositionGetTicket(i)==0','OrderGetTicket(i)==0'):
        assert token in helper
    assert '(!hedging || (ulong)OrderGetInteger(ORDER_MAGIC)==magic)' in helper
    execute=S.split('ExecutionResult ExecuteIntent(',1)[1]
    assert execute.index('ExecutionSymbolAdmissionAllows(ti.symbol,req.magic,preflight_reason)')<execute.index('OrderSend(req, res)')
