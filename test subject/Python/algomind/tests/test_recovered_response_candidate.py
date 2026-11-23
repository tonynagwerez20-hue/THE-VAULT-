"""Response contract oracles/source integration; not native broker proof."""
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/"MQL5/Include/TransactionRecon.mqh").read_text(encoding="utf-8-sig")
E=(ROOT/"MQL5/Include/Execution Engine.mqh").read_text(encoding="utf-8-sig")


def unsigned(text):
    if not text or not text.isascii() or not text.isdigit() or (len(text)>1 and text[0]=="0"):
        raise ValueError
    value=int(text)
    if value>2**64-1:
        raise ValueError
    return value


@pytest.mark.parametrize("value",[0,1,2**53+1,2**63,2**64-1])
def test_unsigned_broker_ids_do_not_pass_through_double(value):
    assert unsigned(str(value))==value


@pytest.mark.parametrize("text",["", "01", "+1", "-1", "1.0", "1e3", " 1", str(2**64),"١"])
def test_invalid_unsigned_identity_rejected(text):
    with pytest.raises(ValueError):
        unsigned(text)


def supports(outcome,send_ok,retcode,order,deal,volume,price,external=0):
    if not send_ok:
        return False
    if outcome==2:
        # REJECT represents one known allowlisted refusal; unknown remains false.
        return retcode=="REJECT" and order==deal==volume==external==0
    if outcome==4:
        return retcode=="DONE" and min(order,deal,volume,price)>0
    return False


@pytest.mark.parametrize("args,expected",[
    ((2,True,"REJECT",0,0,0,0),True),
    ((2,False,"REJECT",0,0,0,0),False),
    ((2,True,"REJECT",7,0,0,0),False),
    ((2,True,"UNKNOWN",0,0,0,0),False),
    ((2,True,"REJECT",0,0,0,0,5),False),
    ((4,True,"DONE",7,9,0.1,2000),True),
    ((4,False,"DONE",7,9,0.1,2000),False),
    ((4,True,"DONE_PARTIAL",7,9,0.1,2000),False),
    ((4,True,"PLACED",7,0,0,0),False),
    ((4,True,"DONE",7,0,0.1,2000),False),
    ((5,True,"DONE",7,9,0.1,2000),False),
])
def test_independent_terminal_outcome_cases(args,expected):
    assert supports(*args)==expected


def test_loader_and_retirement_check_decoded_response_before_acceptance():
    loader=S.split("bool ReconLoadCurrentIntent()",1)[1].split("bool ReconJournalInit(",1)[0]
    assert "ReconDecodeResponse(response,decoded_response)" in loader
    assert "stage!=2 || ReconResponseSupportsOutcome(decoded_response,outcome)" in loader
    finish=S.split("bool ReconFinishOpportunity(",1)[1].split("void TransactionReconHandle(",1)[0]
    assert finish.index("!ReconResponseSupportsOutcome(g_recon_response,outcome)")<finish.index("DatabaseTransactionBegin(")
    assert "return ReconRetcodeIsDefinitiveRejection(retcode);" in E
    assert S.count("case TRADE_RETCODE_REJECT:")==1
    parser=S.split("bool ReconParseULong(",1)[1].split("bool ReconDecodeResponse(",1)[0]
    assert "candidate>(ULONG_MAX-digit)/10" in parser
    assert "StringToDouble" not in parser
    response=S.split("bool ReconDecodeResponse(",1)[1].split("bool ReconResponseSupportsOutcome(",1)[0]
    for check in ("fields)!=10", "retcode>UINT_MAX", "request>UINT_MAX", "external<INT_MIN", "external>INT_MAX"):
        assert check in response
