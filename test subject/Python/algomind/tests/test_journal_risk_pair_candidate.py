"""Source-expression execution against independent restart consistency cases.
Does not execute native storage APIs or establish crash durability.
"""
from pathlib import Path
import re
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/TransactionRecon.mqh').read_text(encoding='utf-8-sig')
EA=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')

def current_predicate(risk_id,risk_outcome,present,journal_id,stage,journal_outcome):
    body=S.split('bool ReconLedgerPairConsistent(',1)[1].split('{',1)[1].split('}',1)[0]
    scope=locals().copy()
    def value(expr):
        expr=expr.replace('&&',' and ').replace('||',' or ')
        expr=re.sub(r'!(?!=)',' not ',expr).replace('false','False').replace('true','True')
        return bool(eval(expr.strip(),{'__builtins__':{}},scope))
    for line in body.splitlines():
        line=line.strip()
        if not line or line.startswith('//'): continue
        match=re.fullmatch(r'if\((.*)\) return (.*);',line)
        if match:
            if value(match[1]): return value(match[2])
        else:
            match=re.fullmatch(r'return (.*);',line)
            assert match,line
            return value(match[1])
    raise AssertionError('no result')

@pytest.mark.parametrize('args,expected',[
 ((0,0,False,0,-1,-1),True), # explicit fresh state, no submission
 ((10,2,False,0,-1,-1),True), # preflight refusal need not submit
 ((10,3,False,0,-1,-1),True),
 ((10,4,False,0,-1,-1),False), # missing evidence for confirmed execution
 ((10,1,False,0,-1,-1),False),
 ((10,5,True,10,1,0),False),
 ((10,4,True,10,2,4),True),
 ((10,2,True,10,2,2),True),
 ((10,2,True,10,2,4),False),
 ((10,4,True,10,2,2),False),
 ((10,3,True,10,2,4),False),
 ((10,6,True,10,2,4),False),
 ((10,4,True,9,2,4),False), # latest confirmed submission absent
 ((10,2,True,9,2,4),True),
 ((10,3,True,9,2,4),True),
 ((10,6,True,9,2,4),True),
 ((10,2,True,11,2,2),False), # risk rollback/journal ahead
 ((10,2,True,10,0,0),False),
 ((10,2,True,10,1,0),False),
 ((0,2,False,0,-1,-1),False),
 ((10,0,False,0,-1,-1),False),
 ((-1,2,False,0,-1,-1),False),
 ((10,7,False,0,-1,-1),False),
 ((10,2,True,0,2,2),False),
 ((10,2,True,10,2,3),False),
])
def test_cross_store_recovery_cases(args,expected):
    assert current_predicate(*args) is expected


def test_real_startup_consumes_loaded_pair_and_never_releases_a_lock():
    init=EA.split('bool risk_state_ready=RiskInit(',1)[1].split('ZeroMemory(g_ext);',1)[0]
    assert init.index('ReconJournalInit(g_cfg)')<init.index('ReconValidateRiskRecovery(')
    assert 'g_risk.last_opportunity_id,g_risk.last_opportunity_outcome' in init
    helper=S.split('bool ReconValidateRiskRecovery(',1)[1].split('bool ReconPrepareIntent(',1)[0]
    for token in ('!risk_ready','!ReconScopeStillCurrent(cfg)','!ReconLoadCurrentIntent()', 'ReconLedgerPairConsistent('):
        assert token in helper
    assert 'RiskReleaseAccountLock' not in helper
    assert 'DatabaseExecute' not in helper
