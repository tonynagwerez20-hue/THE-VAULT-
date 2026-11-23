"""Offline integration contract for bounded orphan reconstruction, not broker proof."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
S=(ROOT/'MQL5/Include/Position Manager.mqh').read_text(encoding='utf-8-sig')
EA=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
B=S.split('bool PositionRecoverMissingFileFromJournal(',1)[1].split('void PositionManagerRemove(',1)[0]

def test_real_startup_fallback_requires_missing_files_and_complete_evidence():
    assert 'if(recovery_status<0 && PositionRecoverMissingFileFromJournal(g_cfg))' in EA
    for gate in ('cfg.shadow_only','ArraySize(g_positions)!=0','!ReconLoadCurrentIntent()',
                 'PositionStateLegacyPresent() || FileIsExist(primary) || FileIsExist(temp)',
                 'ExecutionDealMatchesIntent(', 'ExecutionAggregateOrderDeals(', 'ExecutionCompletedOrderMatches(',
                 'managed!=1','id!=position','ExecutionHasManagedWorkingOrder(cfg)',
                 'sl!=saved.request.sl || tp!=saved.request.tp','current_entry!=price'):
        assert gate in B
        assert B.index(gate)<B.index('PositionManagerRegister(')


def test_original_horizon_policy_and_persistence_required_without_risk_release():
    for field in ('partial_rr','partial_fraction','trail_atr_mult','trail_activate_r','trail_mode','session_end_hour'):
        assert f'management.{field}=saved.management.{field}' in B
    assert 'saved.intent.direction,saved.atr,management,saved.intent.horizon' in B
    assert '!g_position_registration_persisted' in B
    assert 'risk reconciliation still required' in B
    for forbidden in ('RiskReleaseAccountLock(', 'ReconFinishOpportunity(', 'OrderSend(', 'g_position_state_faulted=false'):
        assert forbidden not in B
    register=S.split('void PositionManagerRegister(',1)[1].split('bool PositionRecoverMissingFileFromJournal(',1)[0]
    assert 'g_position_registration_persisted=false;' in register
    assert 'else g_position_registration_persisted=true;' in register
