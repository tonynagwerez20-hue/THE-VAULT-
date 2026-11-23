"""Lock loss model and source integration; no actual terminal concurrency test."""
from pathlib import Path
import math
import pytest
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/Risk Engine.mqh').read_text(encoding='utf-8-sig')


def ownership_valid(owned, saved_key, current_key, token, read_ok, observed, fault=False):
    return (not fault and owned and bool(saved_key) and saved_key==current_key
            and math.isfinite(token) and token>0 and read_ok
            and math.isfinite(observed) and observed==token)


@pytest.mark.parametrize('updates', [dict(owned=False),dict(saved_key=''),
    dict(current_key='other-account'),dict(token=0),dict(token=float('nan')),
    dict(read_ok=False),dict(observed=0),dict(observed=42),
    dict(observed=float('nan')),dict(fault=True)])
def test_lost_or_ambiguous_ownership_is_rejected(updates):
    args=dict(owned=True,saved_key='scope-A',current_key='scope-A',token=123,
              read_ok=True,observed=123)
    args.update(updates)
    assert not ownership_valid(**args)


def test_matching_scope_and_token_permit_nested_ownership():
    assert ownership_valid(True,'A','A',123,True,123)


def test_source_revalidates_nested_acquisition_and_latches_loss():
    acquire=S.split('bool RiskAcquireAccountLock()',1)[1].split('bool RiskReleaseAccountLock()',1)[0]
    assert 'if(g_risk_lock_fault) return false;' in acquire
    assert 'if(g_risk_lock_owned) return RiskVerifyAccountLockOwnership();' in acquire
    assert acquire.index('if(g_risk_lock_fault)') < acquire.index('GlobalVariableTemp(')
    assert 'g_risk_lock_key=key;' in acquire
    verify=S.split('bool RiskVerifyAccountLockOwnership()',1)[1].split('bool RiskAcquireAccountLock()',1)[0]
    for token in ('g_risk_lock_key==RiskOpportunityLockKey()',
                  'GlobalVariableGet(g_risk_lock_key,observed)',
                  'observed==g_risk_lock_token','g_risk_lock_fault=true;',
                  'g_risk.persistence_ok=false;','g_risk_lock_owned=false;'):
        assert token in verify
    assert 'GlobalVariableSet' not in verify


def test_release_cannot_clear_a_foreign_token_or_scope():
    release=S.split('bool RiskReleaseAccountLock()',1)[1].split('double RiskLedgerChecksum',1)[0]
    assert release.index('RiskVerifyAccountLockOwnership()') < release.index('GlobalVariableSetOnCondition(')
    assert 'GlobalVariableSetOnCondition(g_risk_lock_key,0.0,g_risk_lock_token)' in release
    assert 'g_risk_lock_fault=true;' in release
    assert 'GlobalVariableSet(' not in release
