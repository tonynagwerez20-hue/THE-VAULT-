"""Offline completion-order contract; not native crash-durability evidence."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
EA=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
RECON=(ROOT/'MQL5/Include/TransactionRecon.mqh').read_text(encoding='utf-8-sig')

@pytest.mark.parametrize('journal_ok,risk_ok,expected_calls,expected_fault',[
    (False,False,['journal'],'journal'),
    (False,True,['journal'],'journal'),
    (True,False,['journal','risk'],'risk'),
    (True,True,['journal','risk'],None),
])
def test_actual_completion_branch_short_circuits_before_risk_release(journal_ok,risk_ok,expected_calls,expected_fault):
    # Translate only the actual two-branch orchestration, with fault-injected
    # operation results. Expectations above specify the independent contract.
    block=EA.split('   int outcome=OnClosedBar(opportunity_id);',1)[1].split('\n}',1)[0]
    statements=[line.strip() for line in block.splitlines() if line.strip() and not line.strip().startswith('//')]
    assert statements==[
      'if(!ReconFinishOpportunity(opportunity_id,outcome,g_cfg))',
      'PositionManagerLatchStateFault("execution journal cannot retire this opportunity");',
      'else if(!RiskCompleteOpportunity(outcome))',
      'PositionManagerLatchStateFault("opportunity outcome could not be durably committed");']
    calls=[]
    def journal(): calls.append('journal'); return journal_ok
    def risk(): calls.append('risk'); return risk_ok
    translated='\n'.join(statements).replace('if(!ReconFinishOpportunity(opportunity_id,outcome,g_cfg))','if not journal():').replace('else if(!RiskCompleteOpportunity(outcome))','elif not risk():').replace('PositionManagerLatchStateFault("execution journal cannot retire this opportunity");','    fault="journal"').replace('PositionManagerLatchStateFault("opportunity outcome could not be durably committed");','    fault="risk"')
    state=dict(journal=journal,risk=risk,fault=None)
    exec(translated,state)
    assert calls==expected_calls
    assert state['fault']==expected_fault


def test_readback_precedes_clearing_prepared_identity():
    body=RECON.split('bool ReconFinishOpportunity(',1)[1].split('void TransactionReconHandle(',1)[0]
    after=body.split('if(!ReconCommitOne(stmt)) return false;',1)[1]
    assert after.index('!ReconLoadCurrentIntent()')<after.index('g_recon_prepared_id=0')
    for check in ('!g_recon_recovered_present','g_recon_recovered_stage!=2','g_recon_recovered.intent.intent_id!=intent','!ReconResponseSupportsOutcome(g_recon_response,outcome)'):
        assert check in after
