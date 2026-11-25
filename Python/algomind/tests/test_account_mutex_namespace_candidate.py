"""Account mutex namespace/source integration; not native locking evidence."""
from pathlib import Path
import re
import pytest
ROOT=Path(__file__).resolve().parents[3]
SOURCE=(ROOT/'MQL5/Include/Risk Engine.mqh').read_text(encoding='utf-8-sig')
KEY=SOURCE.split('string RiskOpportunityLockKey()',1)[1].split('bool RiskLegacyAdmissionLocksClear()',1)[0]

def namespace(login,server,magic,symbol):
    # Execute current source format strings with the explicitly checked inputs.
    assert 'g_cfg.' not in KEY
    formats=re.findall(r'StringFormat\("([^"]+)"',KEY)
    assert len(formats)==2
    scope=formats[0].replace('%I64d',str(login),1).replace('%s',server,1)
    hashed=146959810
    for ch in scope: hashed=(hashed*16777619+ord(ch))%2147483647
    return formats[1].replace('%I64d',str(login),1).replace('%I64d',str(hashed),1)

@pytest.mark.parametrize('magic,symbol',[(1,'XAUUSD'),(2,'XAUUSD'),(1,'EURUSD'),(999,'BTCUSD')])
def test_same_account_contends_across_strategy_and_symbol(magic,symbol):
    assert namespace(123,'Broker-A',magic,symbol)==namespace(123,'Broker-A',1,'XAUUSD')

def test_distinct_accounts_and_servers_have_distinct_example_keys():
    assert len({namespace(a,s,1,'XAUUSD') for a,s in [(123,'A'),(124,'A'),(123,'B')]})==3

def test_legacy_reservation_checks_precede_new_mutex_acquisition():
    acquire=SOURCE.split('bool RiskAcquireAccountLock()',1)[1].split('bool RiskReleaseAccountLock()',1)[0]
    assert acquire.index('if(!RiskLegacyAdmissionLocksClear()) return false;')<acquire.index('GlobalVariableTemp(key)')
    guard=SOURCE.split('bool RiskLegacyAdmissionLocksClear()',1)[1].split('bool RiskAccountLockWasContended()',1)[0]
    assert 'owner!=0.0' in guard and '!MathIsValidNumber(owner)' in guard
    assert '!GlobalVariableGet(key,owner)' in guard
    assert 'GlobalVariablesTotal()==count' in guard
    assert 'GlobalVariableSet(' not in guard and 'GlobalVariableDel(' not in guard
