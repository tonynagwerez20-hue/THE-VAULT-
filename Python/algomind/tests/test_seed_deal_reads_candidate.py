"""Checked seed-deal property reads; offline source-contract evidence only."""
from pathlib import Path
import re
import pytest
SOURCE=(Path(__file__).resolve().parents[3]/'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig')
BODY=SOURCE.split('bool ExecutionDealMatchesIntent(',1)[1].split('// Aggregate only',1)[0]
PROPS=['DEAL_MAGIC','DEAL_TYPE','DEAL_ENTRY','DEAL_ORDER','DEAL_TIME','DEAL_SYMBOL']

@pytest.mark.parametrize('mask',range(64))
def test_every_unavailable_property_combination_blocks_match(mask):
    # Evaluate the actual source's getter-success disjunction, independent of
    # returned numeric values (BUY/ENTRY_IN may both legitimately be zero).
    clause=BODY[BODY.index('if(!HistoryDealGetInteger'):BODY.index('reason="DEAL_PROPERTIES_UNAVAILABLE"')]
    calls=re.findall(r'!HistoryDealGet(?:Integer|String)\(deal_ticket,(DEAL_\w+),\w+\)',clause)
    assert calls==PROPS
    expression=clause.split('if(',1)[1].rsplit(')',1)[0]
    for index,prop in enumerate(PROPS):
        expression=re.sub(r'!HistoryDealGet(?:Integer|String)\(deal_ticket,'+prop+r',\w+\)',str(not bool(mask & (1<<index))),expression)
    rejected=eval(' '.join(expression.replace('||',' or ').split()),{'__builtins__':{}})
    assert rejected is (mask!=63)


def test_matcher_rejects_older_seed_and_uses_no_unchecked_property_getters():
    assert 'ti.timestamp<=0 || stamp<(long)ti.timestamp' in BODY
    assert BODY.index('DEAL_PROPERTIES_UNAVAILABLE')<BODY.index('if(magic!=')
    assert not re.search(r'HistoryDealGet(?:Integer|String)\(deal_ticket,DEAL_\w+\)',BODY)
