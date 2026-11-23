"""Independent framing oracle and source integration; no native decoder execution."""
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/"MQL5/Include/TransactionRecon.mqh").read_text()


def frame(fields):
    # UTF-16 units match MQL StringLen, including supplementary characters.
    return "".join(str(len(f.encode("utf-16-le"))//2)+":"+f for f in fields)


def unframe(payload):
    units=payload.encode("utf-16-le")
    cursor=0
    fields=[]
    if len(units)>32768:
        raise ValueError("oversize")
    for _ in range(9):
        separator=units.find(b":\x00",cursor)
        if separator<cursor or (separator-cursor)//2>5:
            raise ValueError("length missing")
        length_text=units[cursor:separator].decode("utf-16-le")
        length=int(length_text)
        if str(length)!=length_text or length<0:
            raise ValueError("noncanonical length")
        end=separator+2+length*2
        if end>len(units):
            raise ValueError("truncated")
        fields.append(units[separator+2:end].decode("utf-16-le"))
        cursor=end
    if cursor!=len(units):
        raise ValueError("extra data")
    return fields


FIELDS=["AMIGO_INTENT_V1","XAUUSD","reason:with|delimiters\n😀","XAUUSD","Amigo-17",
        "17|17|103|1|1|0|1|100|160|1|1|3|0","2000|1990|2020|0.8|0.7|0.5|1",
        "1|20260908|0|0|20|0.01|2000|1990|2020","1000|10|0|0.5|2|5|2|0.5|1.5|1|1|0|24"]


def test_exact_fields_roundtrip_without_delimiter_confusion():
    assert unframe(frame(FIELDS))==FIELDS


@pytest.mark.parametrize("payload",["", "-1:a", "01:a", "99999:x", frame(FIELDS)[:-1],
    frame(FIELDS)+"0:", frame(FIELDS[:-1]), "x:"+frame(FIELDS), "0:"*10, "x"*16385])
def test_malformed_framing_rejected(payload):
    with pytest.raises(ValueError):
        unframe(payload)


def test_decoder_checks_numeric_canonical_forms_and_fixed_field_counts():
    integer=S.split("bool ReconParseLong(",1)[1].split("bool ReconParseDouble(",1)[0]
    real=S.split("bool ReconParseDouble(",1)[1].split("bool ReconReadField(",1)[0]
    assert 'StringFormat("%I64d",candidate)!=text' in integer
    assert '!MathIsValidNumber(candidate)' in real
    assert 'StringFormat("%.17g",candidate)!=text' in real
    decoder=S.split("bool ReconDecodePrepared(",1)[1].split("bool ReconRetcodeIsDefinitiveRejection(",1)[0]
    for token in ("integers)!=13", "prices)!=7", "request)!=9", "risk)!=13",
                  "ids[0]!=expected_id", "ids[1]!=ids[0]", "ids[11]<HORIZON_SCALPING",
                  "reqprices[2]!=amounts[1]", "reqprices[3]!=amounts[2]", "mgmt[2]>24"):
        assert token in decoder
    assert decoder.rindex("output=candidate;")>decoder.rindex("return false;")
    assert "candidate.management.shadow_only=true;" in decoder


def test_actual_writer_and_recovery_consume_decoder_without_retiring_pending():
    prepare=S.split("bool ReconPrepareIntent(",1)[1].split("bool ReconRecordResponse(",1)[0]
    assert prepare.index("ReconDecodePrepared(payload,ti.intent_id,verify_payload)")<prepare.index("DatabaseTransactionBegin(")
    init=S.split("bool ReconJournalInit(",1)[1].split("bool ReconPrepareIntent(",1)[0]
    assert init.index("!ReconLoadCurrentIntent()")<init.index("SELECT COUNT(*)")
    assert "if(!ok || unresolved!=0) return ReconJournalFail();" in init
    loader=S.split("bool ReconLoadCurrentIntent()",1)[1].split("bool ReconJournalInit(",1)[0]
    assert "scope==g_recon_scope" in loader
    assert "ReconDecodePrepared(payload,intent,recovered)" in loader
    assert "types==1" in loader and "bool duplicate=DatabaseRead(query)" in loader
    assert "stage>=0 && stage<=2" in loader
    assert "g_recon_recovered=recovered" in loader
    assert "OrderSend(" not in loader
    assert "ReconFinishOpportunity(" not in loader
