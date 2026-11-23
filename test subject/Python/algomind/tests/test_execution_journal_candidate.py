"""Execute SQL extracted from candidate MQL using Python SQLite.
This exercises SQL transitions, not MQL bindings, terminal IO or crash durability.
"""
from pathlib import Path
import re
import sqlite3
from contextlib import closing
from tempfile import TemporaryDirectory
import pytest

ROOT=Path(__file__).resolve().parents[3]
RECON=(ROOT/"MQL5/Include/TransactionRecon.mqh").read_text()
EXEC=(ROOT/"MQL5/Include/Execution Engine.mqh").read_text()
EA=(ROOT/"MQL5/Experts/AMIGO.mq5").read_text()


def strings(body):
    return "".join(re.findall(r'"([^"\n]*)"',body))


SCHEMA=strings(RECON.split('string ReconJournalDDL()',1)[1].split('bool ReconCheckSingleValue(',1)[0])
PREPARE=strings(RECON.split('string sql=',1)[1].split('int stmt=',1)[0])
RESPONSE=strings(RECON.split('bool ReconRecordResponse(',1)[1].split('int stmt=DatabasePrepare(g_recon_db,',1)[1].split(');',1)[0])
FINISH=strings(RECON.split('bool ReconFinishOpportunity(',1)[1].split('int stmt=DatabasePrepare(g_recon_db,',1)[1].split(');',1)[0])
RECOVER=strings(RECON.split('bool ReconJournalInit(',1)[1].split('int query=DatabasePrepare(g_recon_db,',1)[1].split(');',1)[0])


@pytest.fixture
def db():
    connection=sqlite3.connect(":memory:")
    connection.execute(SCHEMA)
    yield connection
    connection.close()


def prepare(db,scope="a:gold",account="a",intent=1,payload="frozen intent"):
    db.execute(PREPARE,(scope,account,intent,payload))
    return db.execute("SELECT changes()").fetchone()[0]


@pytest.fixture
def journal_path():
    with TemporaryDirectory(prefix="amigo-journal-") as directory:
        yield Path(directory)/"journal.sqlite"


def test_prepared_survives_reopen_and_blocks_account_scope(journal_path):
    path=journal_path
    with closing(sqlite3.connect(path)) as first:
        first.execute(SCHEMA)
        assert prepare(first)==1
        first.commit()
    with closing(sqlite3.connect(path)) as recovered:
        assert recovered.execute(RECOVER,("a",)).fetchone()==(1,)
        assert prepare(recovered,scope="a:eur",intent=2)==0
        assert prepare(recovered,scope="b:gold",account="b",intent=2)==1


def test_response_not_completion_and_terminal_commit_required(db):
    assert prepare(db)==1
    db.execute(RESPONSE,("a:gold",1,"order=7 deal=9"))
    assert db.execute(RECOVER,("a",)).fetchone()==(1,)
    db.execute(FINISH,("a:gold",1,4))
    assert db.execute(RECOVER,("a",)).fetchone()==(0,)
    assert prepare(db,intent=1)==0
    assert prepare(db,intent=2)==1


def test_no_response_cannot_be_retired_and_wrong_identity_cannot_update(db):
    prepare(db)
    db.execute(FINISH,("a:gold",1,4))
    assert db.execute("SELECT changes()").fetchone()==(0,)
    db.execute(RESPONSE,("wrong",1,"reply"))
    assert db.execute("SELECT changes()").fetchone()==(0,)
    db.execute(RESPONSE,("a:gold",2,"reply"))
    assert db.execute("SELECT changes()").fetchone()==(0,)


def test_rollback_preserves_preceding_record(db):
    prepare(db)
    db.commit()
    db.execute(RESPONSE,("a:gold",1,"reply"))
    db.rollback()
    assert db.execute("SELECT stage,response FROM execution_journal_v1").fetchone()==(0,"")


def test_bound_payload_is_data_and_roundtrips(db):
    payload="X'; DROP TABLE execution_journal_v1; --\n0:"
    assert prepare(db,payload=payload)==1
    assert db.execute("SELECT payload FROM execution_journal_v1").fetchone()==(payload,)


def test_preparation_precedes_only_send_and_result_capture_precedes_interpretation():
    body=EXEC.split("ExecutionResult ExecuteIntent(",1)[1]
    assert body.count("OrderSend(req, res)")==1
    assert body.index("ReconPrepareIntent(")<body.index("OrderSend(req, res)")
    assert body.index("ReconRecordResponse(")<body.index("if(!send_ok)")
    assert body.index("POST_JOURNAL_INTENT_EXPIRED")<body.index("OrderSend(req, res)")
    assert "r.outcome_uncertain=true;" in body.split("if(!ReconRecordResponse(",1)[1].split("if(!send_ok)",1)[0]


def test_recovery_and_retirement_are_wired_to_actual_ea():
    assert "if(!ReconJournalInit(g_cfg))" in EA
    completion=EA.split("if(!ReconFinishOpportunity(opportunity_id,outcome,g_cfg))",1)[1].split("int OnClosedBar(",1)[0]
    assert "else if(!RiskCompleteOpportunity(outcome))" in completion
    assert "ReconJournalClose();" in EA
    finish=RECON.split("bool ReconFinishOpportunity(",1)[1]
    assert "(outcome!=2 && outcome!=4)" in finish
    assert "if(cfg.shadow_only) return true;" in finish
    assert "ReconVerifyRecord(ti.intent_id,0,payload,false)" in RECON
    assert "ReconVerifyRecord(intent,1,response,true)" in RECON


def test_prepared_payload_contains_intent_risk_and_management_inputs():
    fields=["intent_id","snapshot_id","schema_version","strategy_version","feature_version",
      "model_version","symbol","direction","timestamp","expiry","entry_reference","stop","target",
      "score","confidence","regime","hypothesis","horizon","reason_codes","risk_allocation","risk_modifier","data_quality"]
    body=RECON.split("bool ReconPrepareIntent(",1)[1].split("bool ReconRecordResponse(",1)[0]
    for field in fields:
        assert "ti."+field in body
    for field in ("partial_rr","partial_fraction","trail_atr_mult","trail_activate_r","trail_mode","session_start_hour","session_end_hour"):
        assert "cfg."+field in body
    assert "equity,stop_loss,existing_loss,risk_pct,distortion,atr" in body


def test_competing_connection_cannot_prepare_while_writer_is_active(journal_path):
    with closing(sqlite3.connect(journal_path,timeout=0)) as a, closing(sqlite3.connect(journal_path,timeout=0)) as b:
        a.execute(SCHEMA)
        a.commit()
        assert prepare(a)==1
        with pytest.raises(sqlite3.OperationalError,match="locked"):
            prepare(b,scope="a:eur",intent=2)
        b.rollback()
        a.commit()
        assert prepare(b,scope="a:eur",intent=2)==0


def test_response_is_single_transition_and_rejection_stays_consumed(db):
    prepare(db)
    db.execute(RESPONSE,("a:gold",1,"first response"))
    db.execute(RESPONSE,("a:gold",1,"replacement"))
    assert db.execute("SELECT changes()").fetchone()==(0,)
    db.execute(FINISH,("a:gold",1,2))
    assert db.execute("SELECT response FROM execution_journal_v1").fetchone()==("first response",)
    assert prepare(db,intent=1)==0


def test_unknown_terminal_outcome_keeps_recovery_blocked(db):
    prepare(db)
    db.execute(RESPONSE,("a:gold",1,"reply"))
    db.execute("UPDATE execution_journal_v1 SET stage=2,outcome=5")
    assert db.execute(RECOVER,("a",)).fetchone()==(1,)
    assert prepare(db,intent=2)==0


def schema_evidence(db):
    expected=SCHEMA.replace("IF NOT EXISTS ","")
    return (db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='execution_journal_v1'").fetchall()==[(expected,)]
       and db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND tbl_name='execution_journal_v1'").fetchone()==(0,)
       and db.execute("PRAGMA synchronous").fetchone()==(2,)
       and db.execute("PRAGMA journal_mode").fetchone()==("delete",)
       and db.execute("PRAGMA integrity_check").fetchall()==[("ok",)])


def test_versioned_file_schema_and_effective_settings(journal_path):
    with closing(sqlite3.connect(journal_path)) as db:
        db.execute(SCHEMA)
        db.execute("PRAGMA synchronous=FULL")
        assert schema_evidence(db)
        db.execute("PRAGMA synchronous=OFF")
        assert not schema_evidence(db)


@pytest.mark.parametrize("damage",["constraint", "trigger", "extra_column", "memory_journal"])
def test_altered_existing_schema_or_runtime_mode_is_rejected(journal_path,damage):
    with closing(sqlite3.connect(journal_path)) as db:
        db.execute(SCHEMA.replace("CHECK(intent>0)","") if damage=="constraint" else SCHEMA)
        if damage=="trigger":
            db.execute("CREATE TRIGGER corrupt_reply AFTER INSERT ON execution_journal_v1 BEGIN UPDATE execution_journal_v1 SET response='changed'; END")
        elif damage=="extra_column":
            db.execute("ALTER TABLE execution_journal_v1 ADD COLUMN unexpected TEXT")
        elif damage=="memory_journal":
            db.execute("PRAGMA journal_mode=MEMORY")
        # CREATE IF NOT EXISTS alone succeeds despite every incompatible case.
        db.execute(SCHEMA)
        assert not schema_evidence(db)


def test_native_init_checks_schema_before_recovery_count():
    body=RECON.split("bool ReconJournalInit(",1)[1].split("bool ReconPrepareIntent(",1)[0]
    assert body.index("!ReconJournalSchemaValid()")<body.index("SELECT COUNT(*)")
    helper=RECON.split("bool ReconJournalSchemaValid()",1)[1].split("bool ReconJournalInit(",1)[0]
    for token in ("sqlite_master", "type='trigger'", "PRAGMA synchronous", "PRAGMA journal_mode", "PRAGMA integrity_check"):
        assert token in helper
