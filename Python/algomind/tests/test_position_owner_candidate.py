from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
R=(ROOT/'MQL5/Include/PositionRecovery.mqh').read_text(encoding='utf-8-sig')
EA=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')

def test_lifetime_handle_acquired_before_any_risk_or_position_recovery():
    assert EA.index('PositionStateOwnerAcquire(g_cfg)')<EA.index('RiskInit(InpInitializeRiskLedger)')<EA.index('PositionReconcileState(g_cfg)')
    acquire=R.split('bool PositionStateOwnerAcquire(',1)[1].split('void PositionStateOwnerClose()',1)[0]
    assert 'FileOpen(path,FILE_READ|FILE_WRITE|FILE_BIN)' in acquire
    assert 'FILE_SHARE' not in acquire and 'FileDelete' not in acquire
    assert 'handle==INVALID_HANDLE' in acquire


def test_callbacks_check_owner_and_shutdown_stops_timer_before_close():
    assert 'if(!PositionStateOwnerMatches(g_cfg)) return;' in EA.split('void OnTick()',1)[1]
    timer=EA.split('void OnTimer()',1)[1]
    assert timer.index('PositionStateOwnerMatches(g_cfg)')<timer.index('PositionManagerTick(g_cfg)')
    deinit=EA.split('void OnDeinit(',1)[1].split('void OnTick()',1)[0]
    assert deinit.index('EventKillTimer()')<deinit.index('PositionStateOwnerClose()')
    match=R.split('bool PositionStateOwnerMatches(',1)[1].split('bool PositionStateOwnerAcquire(',1)[0]
    assert 'PositionStatePaths(cfg,' in match and 'GetLastError()==0 && offset==0' in match


def test_handle_probe_checks_error_and_full_runtime_identity():
    match=R.split('bool PositionStateOwnerMatches(',1)[1].split('bool PositionStateOwnerAcquire(',1)[0]
    assert match.index('ResetLastError()')<match.index('FileTell(')<match.index('GetLastError()==0')
    assert 'FileTell(g_position_owner_handle)>=0' not in match
    for token in ('ACCOUNT_SERVER','ACCOUNT_CURRENCY','g_position_owner_margin!=margin','g_position_owner_trade!=trade'):
        assert token in match
    acquire=R.split('bool PositionStateOwnerAcquire(',1)[1].split('void PositionStateOwnerClose()',1)[0]
    assert acquire.index('if(PositionStateOwnerMatches(cfg)) return true;')<acquire.index('FileClose(g_position_owner_handle)')
