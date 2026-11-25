"""Shared-header dependency checks. Not a preprocessor/compiler substitute."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[3]/'MQL5/Include'
HEADERS=['Contracts header.mqh','Configuration.mqh','Logger.mqh','Bar Collector.mqh',
'Orderflow.mqh','Structure Engine.mqh','FVG Engine.mqh','Auction.mqh','Regime Engine.mqh',
'Strategy Engine.mqh','Account Execution Engine.mqh','Execution Engine.mqh',
'Position Manager.mqh','PositionRecovery.mqh']

def test_shared_headers_have_unique_whole_file_guards():
    seen=set()
    for name in HEADERS:
        s=(ROOT/name).read_text(encoding='utf-8-sig').strip()
        lines=s.splitlines()
        assert lines[0].startswith('#ifndef AMIGO_INCLUDE_')
        guard=lines[0].split()[1]
        assert guard not in seen
        seen.add(guard)
        assert lines[1]=='#define '+guard
        assert lines[-1]=='#endif // '+guard


def test_recovery_is_included_after_record_and_storage_declarations():
    s=(ROOT/'Position Manager.mqh').read_text(encoding='utf-8-sig')
    include=s.index('#include <PositionRecovery.mqh>')
    assert s.index('struct PositionState')<s.index('PositionState g_positions[];')<include
    assert include<s.index('bool PositionManagerAdmissionAllowed()')


def test_execution_declares_account_risk_dependency_it_consumes():
    s=(ROOT/'Execution Engine.mqh').read_text(encoding='utf-8-sig')
    assert s.index('#include <Account Execution Engine.mqh>')<s.index('AccountEstimatedStopRisk(')
