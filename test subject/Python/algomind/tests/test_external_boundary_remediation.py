"""Offline behavioral regressions; MQL checks below are SOURCE checks only."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import run_external_service as service
from algomind.schema import parse_kv_file, ExternalContext, SCHEMA_VERSION
from algomind.external import options_adapter, cftc_adapter, news_adapter
NOW = datetime(2026,11,6,12,tzinfo=timezone.utc)

@pytest.mark.parametrize('text', ['a=1\na=1\n','a=1\na=2\n','a=1\nbroken\n','=1\n','a=1\n a = 2'])
def test_ambiguous_payload_rejects_whole_file(tmp_path,text):
    p=tmp_path/'input';p.write_text(text)
    assert parse_kv_file(str(p)) == {}

def test_invalid_encoding_rejects_prefix(tmp_path):
    p=tmp_path/'input';p.write_bytes(b'a=1\n\xff')
    assert parse_kv_file(str(p)) == {}

def test_complete_kv_accepted(tmp_path):
    p=tmp_path/'input';p.write_text('a=1\n\nb=2\n')
    assert parse_kv_file(str(p)) == {'a':'1','b':'2'}

def context(monkeypatch,symbol,data):
    monkeypatch.setattr(service,'_cached_cftc',data)
    monkeypatch.setattr(service,'_last_cftc_fetch',NOW.timestamp())
    monkeypatch.setattr(service,'_cached_news',{'news_valid':False})
    monkeypatch.setattr(service,'_last_news_fetch',NOW.timestamp())
    monkeypatch.setattr(service,'_cached_options',{'options_valid':True,'options_gamma_regime':1})
    snap=SimpleNamespace(symbol=symbol,close=3000,atr14=10) if symbol else None
    monkeypatch.setattr(service,'read_market_snapshot',lambda _:snap)
    with patch.object(service,'options_ctx') as options, patch.object(service,'cftc_ctx') as cftc:
        result=service.build_context('mock',NOW)
    options.assert_not_called();cftc.assert_not_called()
    assert not result.options_valid and service._cached_options is None
    return result

def valid():
    return dict(cftc_valid=True,cftc_publication_verified=True,cftc_publication_ts=int(NOW.timestamp())-86400,
                cftc_net_position=100.,cftc_net_change=2.,cftc_percentile=90.,cftc_extreme=True)

@pytest.mark.parametrize('symbol',['EURUSD','GBPUSD','BTCUSD','XAUUSD.unknown',''])
def test_gold_context_cannot_cross_instruments(monkeypatch,symbol):
    assert not context(monkeypatch,symbol,valid()).cftc_valid

@pytest.mark.parametrize('symbol',['XAUUSD','XAUUSDm'])
def test_verified_complete_gold_fixture_is_accepted(monkeypatch,symbol):
    result=context(monkeypatch,symbol,valid())
    assert result.cftc_valid and result.context_symbol==symbol

@pytest.mark.parametrize('change',[{'cftc_publication_verified':False},{'cftc_publication_ts':0},
    {'cftc_publication_ts':int(NOW.timestamp())+1},{'cftc_publication_ts':int(NOW.timestamp())-14*86400-1},
    {'cftc_net_position':float('nan')},{'cftc_percentile':101},{'cftc_extreme':'1'}])
def test_invalid_provider_evidence_rejected(monkeypatch,change):
    assert not context(monkeypatch,'XAUUSD',{**valid(),**change}).cftc_valid

def test_unmapped_options_never_fetch_or_claim_gamma():
    with patch.object(options_adapter,'fetch_gld_chain') as fetch:
        result=options_adapter.compute_context(3000,10,None,NOW)
    fetch.assert_not_called()
    assert result['options_valid'] is False and result['options_gamma_regime']==0

def test_inferred_cftc_publication_is_not_verified():
    row={'report_date':datetime(2026,10,27,tzinfo=timezone.utc),'long':100,'short':20,'oi':200}
    with patch.object(cftc_adapter,'fetch_gold_managed_money',return_value=[row]):
        result=cftc_adapter.compute_context(NOW)
    assert result['cftc_valid'] is False and result['cftc_publication_verified'] is False

def test_news_explicit_elapsed_duration(monkeypatch):
    monkeypatch.setattr(service,'_last_cftc_fetch',NOW.timestamp())
    monkeypatch.setattr(service,'_last_news_fetch',0)
    monkeypatch.setattr(service,'_cached_news',None)
    monkeypatch.setattr(service,'read_market_snapshot',lambda _:None)
    with patch.object(service,'news_ctx',return_value={'news_valid':False}) as news:
        service.build_context('mock',NOW)
    assert news.call_args.kwargs['reaction_minutes']==15
    assert 'reaction_bars' not in news.call_args.kwargs

def test_serialization_binds_instrument_and_provenance():
    values=dict(line.split('=',1) for line in ExternalContext(context_symbol='XAUUSD').to_kv_lines().splitlines())
    assert values['schema_version']==str(SCHEMA_VERSION)=='104'
    assert values['context_symbol']=='XAUUSD' and values['cftc_pub_verified']=='0'

def test_mql_source_has_independent_fail_closed_boundaries():
    source=(Path(__file__).resolve().parents[3]/'MQL5/Include/External Context Compactor.mqh').read_text(encoding='utf-8-sig')
    for fragment in ['context_symbol!=_Symbol','cftc_fields!=127','!publication_verified',
                     'now-ctx.cftc_publication_ts>14*86400','envelope_fields!=7',
                     'ctx.options_gamma_regime=0;', 'EXTERNAL_PAYLOAD_INVALID',
                     'if(seen_keys[j]==k) payload_valid=false;', 'ExternalFiniteNumber(v)']:
        assert fragment in source

@pytest.mark.parametrize('seconds,active',[(899,True),(900,True),(901,False)])
def test_elapsed_news_window_boundary(seconds,active):
    from datetime import timedelta
    from types import SimpleNamespace
    event=datetime(2026,1,5,14,30,tzinfo=timezone.utc)
    at=event+timedelta(seconds=seconds)
    xml=b"<weeklyevents><event><country>USD</country><impact>High</impact><title>CPI</title><date>01-05-2026</date><time>09:30am</time><forecast>2.0</forecast><actual>2.5</actual></event></weeklyevents>"
    with patch.object(news_adapter.requests,'get',return_value=SimpleNamespace(status_code=200,content=xml)):
        result=news_adapter.compute_context(at,bar_minutes=1,reaction_minutes=15,fetch_completed_at=at)
    assert result['news_valid'] is True
    assert result['news_active_window'] is active
