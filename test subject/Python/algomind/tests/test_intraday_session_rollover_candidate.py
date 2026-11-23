"""Independent server-calendar expiry fixtures; no native clock/runtime proof."""
from datetime import datetime
from pathlib import Path
import pytest
S=(Path(__file__).resolve().parents[3]/'MQL5/Include/Position Manager.mqh').read_text(encoding='utf-8-sig')

def status(opened,now,end):
    if opened<=0 or now<opened or end<0 or end>24: return -1
    if end==0: return 0
    start=datetime.fromtimestamp(opened);current=datetime.fromtimestamp(now)
    if current.date()>start.date(): return 1
    return int(current.hour>=end)

@pytest.mark.parametrize('opened,now,end,expected',[
 ('2026-11-05 10:00','2026-11-05 17:59',18,0),
 ('2026-11-05 10:00','2026-11-05 18:00',18,1),
 ('2026-11-05 10:00','2026-11-06 01:00',18,1),
 ('2026-11-05 10:00','2026-11-05 23:59',24,0),
 ('2026-11-05 10:00','2026-11-06 00:00',24,1),
 ('2026-12-31 23:00','2027-01-01 00:00',24,1),
 ('2028-02-28 23:00','2028-02-29 00:00',24,1),
 ('2026-11-06 10:00','2026-11-09 09:00',18,1),
 ('2026-11-05 10:00','2026-11-06 01:00',0,0),
 ('2026-11-05 10:00','2026-11-05 09:59',18,-1),
 ('2026-11-05 10:00','2026-11-05 11:00',25,-1),
])
def test_session_contract(opened,now,end,expected):
    assert status(datetime.fromisoformat(opened).timestamp(),datetime.fromisoformat(now).timestamp(),end)==expected


def test_actual_date_comparisons_cover_reference_calendar_order():
    body=S.split('int PositionIntradaySessionStatus(',1)[1].split('void PositionManagerTick(',1)[0]
    assert 'current.year>start.year' in body
    assert 'current.year==start.year && current.day_of_year>start.day_of_year' in body
    assert 'return current.hour>=end_hour ? 1 : 0;' in body
    assert 'if(end_hour==0) return 0;' in body
    tick=S.split('void PositionManagerTick(',1)[1]
    assert 'PositionIntradaySessionStatus(g_positions[i].opened,now_t,' in tick
    assert 'if(session_status<0)' in tick
    assert 'dt.hour >= g_positions[i].session_end_hour' not in tick
