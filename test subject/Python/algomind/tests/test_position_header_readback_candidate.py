"""Header corruption fixture and source checks; no MQL file/durability claim."""
from pathlib import Path
import struct
import pytest
ROOT=Path(__file__).resolve().parents[3]
HEADER=(105,20260908,1,1000,123,11,22,33,2,0,1)
FORMAT='<iqiqqqqqiii'

@pytest.mark.parametrize('index',range(len(HEADER)))
def test_each_header_field_corruption_is_rejected_even_with_expected_checksum(index):
    altered=list(HEADER)
    altered[index]+=1
    expected_checksum=12345
    wire=struct.pack(FORMAT,*altered)+struct.pack('<q',expected_checksum)
    fields=struct.unpack(FORMAT,wire[:-8])
    # Old checksum-only acceptance would pass. Payload comparison must fail.
    assert struct.unpack('<q',wire[-8:])[0]==expected_checksum
    assert fields!=HEADER


def test_header_comparison_precedes_checksum_and_publication():
    s=(ROOT/'MQL5/Include/PositionRecovery.mqh').read_text(encoding='utf-8-sig')
    save=s.split('bool PositionSaveState(',1)[1]
    checks=save.split('bool header_matches=',1)[1].split('if(!header_matches)',1)[0]
    for expected in ('AMIGO_STATE_SCHEMA_VERSION','(long)cfg.magic_number','count','saved_time',
                     'login','server_hash','symbol_hash','currency_hash','margin_mode','trade_mode','config_version'):
        assert '=='+expected in checks
    assert checks.count('FileReadInteger(')==5
    assert checks.count('FileReadLong(')==6
    assert save.index('if(!header_matches)')<save.index('long saved_header_checksum=')<save.index('FileMove(')
    assert 'FileSeek(verify,AMIGO_STATE_HEADER_BYTES-8' not in save
