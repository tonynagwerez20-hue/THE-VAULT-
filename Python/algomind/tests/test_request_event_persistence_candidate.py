"""SQL persistence tests for actual callback artifact; no native event execution."""
from pathlib import Path
import re
import sqlite3
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/TransactionRecon.mqh').read_text(encoding='utf-8-sig')
EA=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
def strings(s): return ''.join(re.findall(r'"([^"\n]*)"',s))
DDL=strings(S.split('string ReconEventDDL()',1)[1].split('bool ReconEventSchemaValid()',1)[0])
BODY=S.split('bool ReconCaptureRequestEvent(',1)[1].split('//--- Called from AMIGO',1)[0]
SQL=strings(BODY.split('int stmt=DatabasePrepare(g_recon_db,',1)[1].split(');',1)[0])

@pytest.mark.parametrize('next_row,changed,expected',[
 (('scope',10,'reply'),1,('scope',10,'reply')),
 (('scope',10,'conflict'),0,('scope',10,'reply')),
 (('scope',9,'older'),0,('scope',10,'reply')),
 (('scope',11,'newer'),1,('scope',11,'newer')),
])
def test_actual_sql_retains_conflicts_and_accepts_identical_duplicates(next_row,changed,expected):
    db=sqlite3.connect(':memory:')
    try:
        db.execute(DDL);db.execute(SQL,('scope',10,'reply'));db.commit()
        db.execute(SQL,next_row)
        assert db.execute('SELECT changes()').fetchone()==(changed,)
        assert db.execute('SELECT * FROM execution_request_event_v1').fetchone()==expected
    finally: db.close()


def test_scope_separation_and_interrupted_transaction():
    db=sqlite3.connect(':memory:')
    try:
        db.execute(DDL);db.execute(SQL,('A',10,'first'));db.commit()
        db.execute(SQL,('A',11,'uncommitted'));db.rollback()
        db.execute(SQL,('B',10,'other'));db.commit()
        assert db.execute('SELECT * FROM execution_request_event_v1 ORDER BY scope').fetchall()==[('A',10,'first'),('B',10,'other')]
    finally: db.close()


def test_callback_uses_only_request_events_and_current_session_identity():
    assert 'trans.type==TRADE_TRANSACTION_REQUEST && !ReconCaptureRequestEvent(request,result,g_cfg)' in EA
    assert 'g_recon_session_request==0 || result.request_id!=g_recon_session_request' in BODY
    assert 'g_recon_recovered.intent.intent_id!=g_recon_session_intent' in BODY
    for field in ('action','magic','symbol','comment','type','type_filling','volume','price','sl','tp','deviation'):
        assert f'request.{field}!=saved.{field}' in BODY
    for forbidden in ('OrderSend(', 'RiskReleaseAccountLock(', 'ReconFinishOpportunity(', 'HistorySelect('):
        assert forbidden not in BODY
    assert 'UPDATE execution_journal_v1' not in BODY
    assert BODY.index('!ReconDecodeResponse(')<BODY.index('DatabaseTransactionBegin(')
    assert BODY.index('!ReconCommitOne(stmt)')<BODY.index('actual==response')
