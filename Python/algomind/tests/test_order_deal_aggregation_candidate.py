"""Independent deal aggregation expectations and MQL source integration checks.
No native history or broker execution is exercised.
"""
from decimal import Decimal
from pathlib import Path
import pytest

SOURCE=(Path(__file__).resolve().parents[3]/"MQL5/Include/Execution Engine.mqh").read_text()


def aggregate(deals, seed=11):
    # Fixture identity is independently fixed: order 7, position 9, magic 13,
    # XAUUSD buy opening deals, observed no earlier than the intent at 100.
    if not 0<len(deals)<=4096:
        return None
    seen=set()
    volume=Decimal(0)
    cost=Decimal(0)
    for d in deals:
        ticket,order,position,magic,symbol,side,entry,stamp,v,p=d
        if ticket<=0 or ticket in seen or (order,position,magic,symbol,side,entry)!=(7,9,13,"XAUUSD",1,"IN") or stamp<100:
            return None
        seen.add(ticket)
        v,p=Decimal(str(v)),Decimal(str(p))
        if not v.is_finite() or not p.is_finite() or v<=0 or p<=0:
            return None
        volume+=v
        cost+=v*p
    return (volume,cost/volume) if seed in seen else None


D1=(11,7,9,13,"XAUUSD",1,"IN",100,"0.02","2000")
D2=(12,7,9,13,"XAUUSD",1,"IN",101,"0.03","2010")


def test_split_fill_volume_and_weighted_price():
    assert aggregate([D1,D2])==(Decimal("0.05"),Decimal("2006"))
    assert aggregate([D2,D1])==aggregate([D1,D2])
    assert aggregate([D1])==(Decimal("0.02"),Decimal("2000"))


@pytest.mark.parametrize("index,value",[(0,11),(1,8),(2,10),(3,14),(4,"EURUSD"),
    (5,-1),(6,"OUT"),(7,99),(8,"0"),(8,"NaN"),(9,"Infinity"),(9,"-1")])
def test_duplicate_or_conflicting_deal_blocks_aggregate(index,value):
    bad=list(D2)
    bad[index]=value
    assert aggregate([D1,tuple(bad)]) is None


def test_empty_missing_seed_and_excess_history_block():
    assert aggregate([]) is None
    assert aggregate([D2]) is None
    assert aggregate([D1]*4097) is None


def test_actual_execution_consumes_aggregate_before_volume_decision():
    body=SOURCE.split("if(res.retcode == TRADE_RETCODE_DONE ||",1)[1]
    aggregate_call=body.index("ExecutionAggregateOrderDeals(")
    assert aggregate_call<body.index("bool response_mismatch=")
    assert "r.fill_volume,r.fill_price,aggregate_reason" in body
    failure=body[aggregate_call:body.index("double volume_tolerance=")]
    assert "r.outcome_uncertain=true;" in failure and "return r;" in failure
    assert "res.retcode==TRADE_RETCODE_DONE_PARTIAL || volume_mismatch" in body


def test_snapshot_reads_are_bounded_checked_and_outputs_committed_last():
    body=SOURCE.split("bool ExecutionAggregateOrderDeals(",1)[1].split("// Only server responses",1)[0]
    assert "count>4096" in body and "tickets[i]==tickets[i-1]" in body
    assert "!HistorySelectByPosition(position)" in body
    assert "HistoryDealSelect(" not in body
    for field in ("DEAL_ORDER","DEAL_POSITION_ID","DEAL_MAGIC","DEAL_TYPE","DEAL_ENTRY","DEAL_TIME"):
        assert f"!HistoryDealGetInteger(ticket,{field}," in body
    assert "if(!seed_found" in body and "HistoryDealsTotal()!=count" in body
    assert body.index("volume=total_volume;")>body.index("if(!seed_found")
    assert body.index("price=average;")>body.index("if(!MathIsValidNumber(average)")
