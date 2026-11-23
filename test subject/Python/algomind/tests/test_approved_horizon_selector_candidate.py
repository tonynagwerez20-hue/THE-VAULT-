"""Exhaustive source-expression/reference comparison; NOT native MQL execution."""
from itertools import product
from pathlib import Path
import re
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/"MQL5/Include/Strategy Engine.mqh").read_text()
E=(ROOT/"MQL5/Experts/AMIGO.mq5").read_text()
T=(ROOT/"MQL5/Include/Structure Engine.mqh").read_text()
BODY=S.split("bool SelectApprovedHorizon(",1)[1].split("//--- Mean-reversion evidence",1)[0]
FIELDS=("d1_dir","h4_dir","h1_dir","m30_dir","m15_dir","m5_dir","m1_dir")
N={0,1}
# Independent approved table, normalized to trade direction +1.
TABLE={"CONT": [("SWING",[{1},{1},{1},N,N,{1},{1}]),
                ("INTRADAY",[N,N,{1},{1},{1},{1},{1}]),
                ("SCALPING",[N,N,N,N,N,{1},{1}])],
       "MR": [("INTRADAY",[N,N,{0},{0},{0},N,{1}]),
              ("SCALPING",[N,N,N,N,{0},{0},{1}])]}


def expected(vector,d,strategy):
    for horizon,allowed in TABLE[strategy]:
        if all(value*d in choices for value,choices in zip(vector,allowed)):
            return horizon
    return None


def source_expressions(vector,d,strategy):
    # Evaluate the actual branch predicates extracted from source. This only
    # translates this pure expression subset, not the surrounding MQL runtime.
    if any(v not in (-1,0,1) or v==-d for v in vector) or vector[-1]!=d:
        return None
    td=SimpleNamespace(**dict(zip(FIELDS,vector)))
    if strategy=="CONT":
        if td.m5_dir!=d:
            return None
        branch=BODY.split("if(decision.hypothesis==HYP_CONTINUATION)",1)[1].split("if(decision.hypothesis==HYP_MEAN_REVERSION",1)[0]
    else:
        branch=BODY.split("if(decision.hypothesis==HYP_MEAN_REVERSION",1)[1]
    predicates=re.findall(r'(?:if|else if)\((td[^)]*)\)\s*horizon=HORIZON_(\w+);',branch)
    assert len(predicates)==2
    for expression,horizon in predicates:
        assert re.fullmatch(r'[a-z0-9_.= &]+',expression)
        if eval(expression.replace("&&","and"),{"__builtins__":{}},{"td":td,"d":d}):
            return horizon
    return "SCALPING" if strategy=="CONT" else None


def test_all_8748_direction_strategy_cases_match_approved_table():
    for vector in product((-1,0,1),repeat=7):
        for d in (-1,1):
            for strategy in ("CONT","MR"):
                assert source_expressions(vector,d,strategy)==expected(vector,d,strategy),(vector,d,strategy)


def test_golden_cases_and_longest_context_tie():
    assert source_expressions((1,1,1,1,1,1,1),1,"CONT")=="SWING"
    assert source_expressions((0,0,1,1,1,1,1),1,"CONT")=="INTRADAY"
    assert source_expressions((0,0,0,0,0,1,1),1,"CONT")=="SCALPING"
    assert source_expressions((0,0,0,0,0,0,1),1,"MR")=="INTRADAY"
    assert source_expressions((0,0,1,0,0,0,1),1,"MR")=="SCALPING"


def test_missing_invalid_and_no_signal_guards_are_explicit():
    for text in ("!td.complete", "td.asof_boundary!=boundary", "boundary<=0",
                 "decision.action!=ACTION_TRADE", "decision.direction!=1 && decision.direction!=-1",
                 "dirs[i]<-1 || dirs[i]>1 || dirs[i]==-d", "regime==REGIME_BALANCED"):
        assert text in BODY
    assert BODY.index("horizon=(ENUM_HORIZON)0;")<BODY.index("if(!td.complete")
    top=T.split("bool EvaluateTopDownContext(",1)[1]
    assert top.index("td.complete=false;")<top.index("TryEvaluateClosedStructure(")
    assert top.index("td.complete=true;")>top.rindex("TryEvaluateClosedStructure(")


def test_m1_and_existing_proxy_gates_precede_frozen_horizon():
    assert "InpTFExec   = PERIOD_M1;" in E
    assert "InpTFExec!=PERIOD_M1 || InpTFM5!=PERIOD_M5" in E
    body=E.split("int OnClosedBar(",1)[1].split("void OnTradeTransaction(",1)[0]
    selection=body.index("SelectApprovedHorizon(td,dr,rs.regime,decision_boundary,selected_horizon)")
    assert body.index("ScoreStrategies(decision_feat, g_ext, g_cfg)")<selection
    assert body.index("if(dr.action != ACTION_TRADE)")<selection
    assert body.index("if(!g_cfg.tick_pressure_enabled)")<selection
    assert selection<body.index("RiskAllows(g_cfg, risk_reason)")
    assert body.count("dr.horizon=selected_horizon;")==1
    assert "selected_horizon = HORIZON_INTRADAY" not in body
    assert "if(g_cfg.tf_exec == PERIOD_M1) selected_horizon" not in body
