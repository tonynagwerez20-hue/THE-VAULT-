"""Actual adapter tests and explicit reference/source tests; no native execution."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from algomind.external import news_adapter as news
ROOT=Path(__file__).resolve().parents[3]

@pytest.mark.parametrize('seconds,retained,blackout',[(60,True,True),(300,True,True),(900,True,True),(901,True,False),(3600,True,False),(14400,True,False),(14401,False,False)])
def test_actual_adapter_retention_independent_of_blackout(seconds,retained,blackout):
    release=datetime(2026,11,6,12,tzinfo=timezone.utc);now=release+timedelta(seconds=seconds)
    event=SimpleNamespace(scheduled_ts=release,forecast='2',actual='3')
    with patch.object(news,'fetch_news_events',return_value=[event]):
        result=news.compute_context(now,fetch_completed_at=now,reaction_minutes=15)
    assert result['news_valid']
    assert result['news_released'] is retained
    assert result['news_active_window'] is blackout
    assert result['news_event_ts']==(int(release.timestamp()) if retained else 0)

@pytest.mark.parametrize('horizon,elapsed,want',[(1,59,False),(1,60,True),(1,300,True),(1,301,False),
 (2,299,False),(2,300,True),(2,3600,True),(2,3601,False),
 (3,3599,False),(3,3600,True),(3,14400,True),(3,14401,False),(0,600,False)])
def test_independently_specified_horizon_windows(horizon,elapsed,want):
    bounds={1:(60,300),2:(300,3600),3:(3600,14400)}
    limits=bounds.get(horizon)
    allowed=limits is not None and limits[0]<=elapsed<=limits[1]
    assert allowed is want

def test_source_final_gate_precedes_geometry_and_preserves_saved_horizon():
    expert=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
    block=expert.split('   dr.horizon=selected_horizon;',1)[1]
    assert block.index('AmigoNewsHorizonAllows(')<block.index('//--- 9) Entry geometry')
    assert 'return RISK_OP_REJECTED;' in block.split('LogMsg(LOG_INFO,"FROZEN_FOOTPRINT"',1)[0]
    assert 'ti.horizon          = dr.horizon;' in expert
    policy=(ROOT/'MQL5/Include/News Policy.mqh').read_text()
    for token in ['minimum=60; maximum=300','minimum=300; maximum=3600','minimum=3600; maximum=14400',
                  'ctx.news_observed_ts-ctx.news_event_ts<minimum','NEWS_HORIZON_INVALID']:
        assert token in policy
