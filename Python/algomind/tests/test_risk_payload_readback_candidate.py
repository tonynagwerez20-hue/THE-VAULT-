"""Independent checksum-collision example and exact ledger readback checks."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def test_checksum_collision_is_not_equal_payload():
    expected=dict(generation=1,start=1000,peak=1100)
    corrupted=dict(generation=1,start=1005,peak=1097)
    def checksum(s): return s['generation']+3*s['start']+5*s['peak']
    assert checksum(expected)==checksum(corrupted)
    assert expected!=corrupted


def test_writer_compares_every_persisted_field_after_readback():
    s=(ROOT/'MQL5/Include/Risk Engine.mqh').read_text(encoding='utf-8-sig')
    writer=s.split('bool RiskLedgerSlotWrite(',1)[1].split('void RiskCopyAccountFields',1)[0]
    fields=['generation','start_of_day_equity','peak_equity','daily_locked','total_locked',
            'last_day','initial_equity','adaptive_high_water','adaptive_last_equity',
            'last_opportunity_bar','last_opportunity_id','last_opportunity_outcome']
    for field in fields:
        assert f'verify.{field}==s.{field}' in writer
    assert writer.index('GlobalVariablesFlush()')<writer.index('RiskLedgerSlotRead(prefix,slot,verify)')
