"""SOURCE checks only; these do not execute the native tester."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def test_news_backtest_rejects_before_account_and_state_initialization():
    s=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
    init=s.split('int OnInit()',1)[1].split('void OnDeinit',1)[0]
    gate=init.index('Historical news replay and broker-to-UTC mapping')
    assert '&& InpNewsMode!=0' in init[:gate]
    assert init.index('MQLInfoInteger(MQL_TESTER)')<gate<init.index('AccountInfoInteger(ACCOUNT_LOGIN)')
    assert 'return INIT_PARAMETERS_INCORRECT;' in init[gate:init.index('if(InpNewsBufferMins')]
def test_tester_reader_resets_provider_flags_and_rejects_before_file_access():
    s=(ROOT/'MQL5/Include/External Context Compactor.mqh').read_text(encoding='utf-8-sig')
    reader=s.split('bool ReadExternalContext(',1)[1].split('bool ExternalNewsFilterAllows(',1)[0]
    gate=reader.index('LIVE_EXTERNAL_BRIDGE_DISABLED_IN_TESTER')
    assert reader.index('ctx.news_valid               = false')<gate<reader.index('FileOpen(')
    assert reader.index('ctx.cftc_valid               = false')<gate
    assert reader.index('ctx.options_valid            = false')<gate
    assert 'return false;' in reader[gate:reader.index('FileOpen(')]
def test_tester_market_publication_returns_before_any_filesystem_access():
    s=(ROOT/'MQL5/Include/External Context Compactor.mqh').read_text(encoding='utf-8-sig')
    writer=s.split('void WriteSnapshotForExternal(',1)[1]
    guard='if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION)) return;'
    assert writer.index(guard)<writer.index('FileIsExist(')<writer.index('FileOpen(')
