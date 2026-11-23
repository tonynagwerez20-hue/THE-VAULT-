"""Independent scope identity fixtures plus real producer/consumer checks."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/"MQL5/Include/TransactionRecon.mqh").read_text(encoding="utf-8-sig")
E=(ROOT/"MQL5/Include/Execution Engine.mqh").read_text(encoding="utf-8-sig")


def scope(login,server,currency,magic,symbol):
    if login<=0 or not server or not currency or not symbol:
        return None
    return "".join(f"{len(str(x))}:{x}" for x in (login,server,currency,magic,symbol))


BASE=(123,"broker-A","USD",777,"XAUUSD")


@pytest.mark.parametrize("index,value",[(0,124),(1,"broker-B"),(2,"EUR"),(3,778),(4,"EURUSD"),
    (0,0),(1,""),(2,""),(4,"")])
def test_account_or_strategy_scope_change_is_not_same_identity(index,value):
    changed=list(BASE)
    changed[index]=value
    assert scope(*changed)!=scope(*BASE)


def test_delimiters_cannot_alias_different_components():
    assert scope(1,"a:b","c",7,"gold")!=scope(1,"a","b:c",7,"gold")
    assert scope(*BASE)==scope(*BASE)


def test_writer_and_retirement_recheck_current_identity():
    helper=S.split("bool ReconScopeStillCurrent(",1)[1].split("void ReconJournalClose()",1)[0]
    assert "account!=g_recon_account" in helper and "scope==g_recon_scope" in helper
    for field in ("ACCOUNT_LOGIN","ACCOUNT_SERVER","ACCOUNT_CURRENCY"):
        assert field in S.split("string ReconCurrentAccountScope()",1)[1].split("bool ReconScopeStillCurrent(",1)[0]
    prepare=S.split("bool ReconPrepareIntent(",1)[1].split("bool ReconRecordResponse(",1)[0]
    assert prepare.index("!ReconScopeStillCurrent(cfg)")<prepare.index("DatabaseTransactionBegin(")
    assert "req.magic!=cfg.magic_number" in prepare and "req.symbol!=cfg.symbol" in prepare
    finish=S.split("bool ReconFinishOpportunity(",1)[1].split("void TransactionReconHandle(",1)[0]
    assert finish.index("!ReconScopeStillCurrent(cfg)")<finish.index("DatabaseTransactionBegin(")
    execute=E.split("ExecutionResult ExecuteIntent(",1)[1]
    prepare_call=execute.index("ReconPrepareIntent(")
    fresh=execute.index("!ReconScopeStillCurrent(cfg)",prepare_call)
    assert prepare_call<fresh<execute.index("OrderSend(req, res)")
