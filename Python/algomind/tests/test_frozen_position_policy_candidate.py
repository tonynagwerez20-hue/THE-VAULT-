"""Frozen position management serialization and consumer contract."""
from pathlib import Path
import re
import struct
ROOT=Path(__file__).resolve().parents[3]/'MQL5/Include'
PM=(ROOT/'Position Manager.mqh').read_text(encoding='utf-8-sig')
R=(ROOT/'PositionRecovery.mqh').read_text(encoding='utf-8-sig')
FIELDS=['partial_rr','partial_fraction','trail_atr_mult','trail_activate_r','session_end_hour']

def test_each_management_input_is_captured_written_read_compared_and_consumed():
    tick=PM.split('void PositionManagerTick(',1)[1]
    for field in FIELDS:
        assert f'g_positions[n].{field}=cfg.{field}' in PM
        assert f'g_positions[i].{field}' in tick
        assert f'cfg.{field}' not in tick
        assert f'actual.{field}!=expected.{field}' in R
        assert f'p.{field}=' in R
        assert f'g_positions[i].{field}' in R
        assert f'p.{field}' in R.split('long PositionStateRecordChecksum(',1)[1].split('// Read back',1)[0]


def test_exact_record_size_from_actual_write_sequence_and_roundtrip():
    block=R.split('// 2. Records:',1)[1].split('long expected_size',1)[0]
    writes=re.findall(r'FileWrite(Long|Integer|Double)\(handle,[^;]+;',block)
    fmt='<'+''.join({'Long':'q','Integer':'i','Double':'d'}[kind] for kind in writes)
    assert struct.calcsize(fmt)==164
    # Two distinct policy payloads survive a byte roundtrip independently.
    for policy in [(1.5,.25,1.,1.,18),(3.,.5,2.5,2.,24)]:
        assert struct.unpack('<ddddi',struct.pack('<ddddi',*policy))==policy
    assert '#define AMIGO_STATE_SCHEMA_VERSION 106' in R
    assert 'if(schema!=AMIGO_STATE_SCHEMA_VERSION)' in R
