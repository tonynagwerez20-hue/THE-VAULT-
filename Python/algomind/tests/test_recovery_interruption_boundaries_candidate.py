"""Cross-store interruption scenarios using candidate SQL and pair predicate.
Closing/reopening SQLite is not a power-loss simulation or native MQL test.
"""
from pathlib import Path
import importlib.util
import sqlite3
from tempfile import TemporaryDirectory
import pytest
HERE=Path(__file__).parent

def load(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
J=load('test_execution_journal_candidate')
P=load('test_journal_risk_pair_candidate')

@pytest.mark.parametrize('cut,expected_stage,expected_pending,expected_pair',[
 ('prepared',0,1,False),
 ('response_uncommitted',0,1,False),
 ('response_committed',1,1,False),
 ('position_saved',1,1,False),
 ('journal_completion_uncommitted',1,1,False),
 ('journal_complete_risk_reserved',2,0,False),
 ('both_complete',2,0,True),
])
def test_reopen_at_each_completion_boundary(cut,expected_stage,expected_pending,expected_pair):
    with TemporaryDirectory(prefix='amigo-recovery-boundary-') as directory:
        path=Path(directory)/'journal.sqlite'
        db=sqlite3.connect(path)
        db.execute(J.SCHEMA)
        assert J.prepare(db,intent=10)==1
        db.commit()
        risk_outcome=1 # independently modeled durable RESERVED state
        if cut!='prepared':
            db.execute(J.RESPONSE,('a:gold',10,'confirmed response evidence'))
            if cut!='response_uncommitted': db.commit()
        if cut in ('journal_completion_uncommitted','journal_complete_risk_reserved','both_complete'):
            db.execute(J.FINISH,('a:gold',10,4))
            if cut!='journal_completion_uncommitted': db.commit()
        if cut=='both_complete': risk_outcome=4
        db.close() # uncommitted transactions roll back; no crash durability claim
        db=sqlite3.connect(path)
        try:
            row=db.execute('SELECT intent,stage,outcome FROM execution_journal_v1').fetchone()
            assert row==(10,expected_stage,4 if expected_stage==2 else 0)
            assert db.execute(J.RECOVER,('a',)).fetchone()==(expected_pending,)
            assert P.current_predicate(10,risk_outcome,True,*row)==expected_pair
            # Consumed identity cannot reopen even when journal completed.
            assert J.prepare(db,intent=10)==0
            # Writing a position file is not a risk/journal completion operation.
            if cut=='position_saved':
                assert row[1]==1 and not expected_pair
        finally: db.close()


def test_reconstruction_does_not_complete_or_unlock_opportunity():
    pm=(J.ROOT/'MQL5/Include/Position Manager.mqh').read_text(encoding='utf-8-sig')
    body=pm.split('bool PositionRecoverMissingFileFromJournal(',1)[1].split('void PositionManagerRemove(',1)[0]
    for forbidden in ('RiskCompleteOpportunity(', 'ReconFinishOpportunity(', 'RiskReleaseAccountLock(', 'GlobalVariableSetOnCondition('):
        assert forbidden not in body
    assert 'risk reconciliation still required' in body
