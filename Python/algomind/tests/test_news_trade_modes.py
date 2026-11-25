"""News adapter behavior + independent MQL policy expectations (not native execution)."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from types import SimpleNamespace
import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from algomind.external import news_adapter as news
ROOT=Path(__file__).resolve().parents[3]

def expected(mode, *, valid=True, fresh=True, active=True, released=True, elapsed=60, observed_elapsed=60):
    if mode==0:return True
    if mode not in (1,2,3) or not valid or not fresh:return False
    if mode==1:return not active
    if not active and not released:return mode==3
    return released and 60<=elapsed<=14400 and observed_elapsed>=60

@pytest.mark.parametrize('mode,changes,want',[
 (0,{'valid':False},True),(1,{},False),(2,{},True),(3,{},True),
 (2,{'active':False,'released':False},False),(3,{'active':False,'released':False},True),
 (2,{'released':False},False),(3,{'released':False},False),
 (2,{'elapsed':59},False),(2,{'elapsed':900},True),(2,{'elapsed':14401},False),
 (2,{'observed_elapsed':59},False),(2,{'fresh':False},False),(3,{'valid':False},False),
 (4,{},False),(-1,{},False)])
def test_independent_admission_table(mode,changes,want):
    assert expected(mode,**changes) is want

def event(offset,actual='2.5'):
    at=datetime(2026,11,6,12,tzinfo=timezone.utc)+timedelta(seconds=offset)
    return SimpleNamespace(scheduled_ts=at,forecast='2.0',actual=actual)

@pytest.mark.parametrize('events',[[event(-120),event(120)],[event(120),event(-120)]])
def test_overlapping_future_event_blocks_released_catalyst(events):
    now=datetime(2026,11,6,12,tzinfo=timezone.utc)
    with patch.object(news,'fetch_news_events',return_value=events):
        result=news.compute_context(now,fetch_completed_at=now,reaction_minutes=15)
    assert result['news_valid'] and result['news_active_window']
    assert not result['news_released']
    assert result['news_event_ts']==int((now+timedelta(seconds=120)).timestamp())

def test_latest_release_selected_independently_of_provider_order():
    now=datetime(2026,11,6,12,tzinfo=timezone.utc)
    with patch.object(news,'fetch_news_events',return_value=[event(-800),event(-120)]):
        result=news.compute_context(now,fetch_completed_at=now,reaction_minutes=15)
    assert result['news_released'] and result['news_event_ts']==int(now.timestamp())-120

@pytest.mark.parametrize('actual',['nan','inf','-inf',''])
def test_nonfinite_or_absent_actual_cannot_confirm_release(actual):
    now=datetime(2026,11,6,12,tzinfo=timezone.utc)
    with patch.object(news,'fetch_news_events',return_value=[event(-120,actual)]):
        result=news.compute_context(now,fetch_completed_at=now,reaction_minutes=15)
    assert not result['news_released']

def test_source_shared_policy_and_live_boundary():
    policy=(ROOT/'MQL5/Include/News Policy.mqh').read_text()
    strategy=(ROOT/'MQL5/Include/Strategy Engine.mqh').read_text()
    reader=(ROOT/'MQL5/Include/External Context Compactor.mqh').read_text()
    expert=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text()
    assert 'AmigoNewsAdmission(ext,cfg.news_mode,news_now,' in strategy
    assert 'return AmigoNewsAdmission(ctx,mode,now,max_age_seconds,reason);' in reader
    for token in ['elapsed<60','elapsed>14400','ctx.news_observed_ts-ctx.news_event_ts<60','NEWS_RELEASE_UNCONFIRMED','NEWS_NO_RELEASE_SETUP']:
        assert token in policy
    assert 'outcome_fields!=3' in reader and 'ExternalFiniteNumber(v)' in reader
    assert 'if(InpNewsMode<0 || InpNewsMode>3)' in expert
    assert 'InpShadowOnly        = true' in expert
