"""Saved-horizon management integration, not broker runtime validation."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]/'MQL5'
P=(ROOT/'Include/Position Manager.mqh').read_text(encoding='utf-8-sig')
R=(ROOT/'Include/PositionRecovery.mqh').read_text(encoding='utf-8-sig')
E=(ROOT/'Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')

def test_saved_policy_veto_precedes_live_lookup_and_shadow_actions():
    b=P.split('void PositionManagerTick(',1)[1]
    assert b.index('PositionSavedHorizonPolicyValid(g_positions[i],now_t)')<b.index('PositionSelectByIdentifier(pid, position_ticket)')
    guard=P.split('bool PositionSavedHorizonPolicyValid(',1)[1].split('void PositionManagerTick(',1)[0]
    for token in ['p.horizon<HORIZON_SCALPING','p.horizon>HORIZON_SWING','now<p.opened','p.partial_fraction>=1.0','p.session_end_hour>24','p.trailing_mode!=TRAIL_OFF']:assert token in guard
    assert 'g_cfg' not in guard

def test_each_position_retains_original_horizon_through_registration_and_restart():
    assert 'g_positions[n].horizon               = horiz;' in P
    assert 'ENUM_HORIZON horiz = g_positions[i].horizon;' in P
    for token in ['(int)p.horizon','actual.horizon!=expected.horizon','p.horizon               = (ENUM_HORIZON)FileReadInteger','(int)g_positions[i].horizon']:assert token in R
    assert 'saved.intent.horizon' in P
    assert 'PositionManagerRegister' in E and 'dr.horizon' in E

def test_horizon_specific_existing_management_remains_distinct():
    for token in ['if(horiz == HORIZON_SCALPING) be_ratio = 0.33;','else if(horiz == HORIZON_SWING) be_ratio = 0.60;','(horiz == HORIZON_SCALPING) ? 1.5 : g_positions[i].partial_rr','(horiz == HORIZON_SCALPING) ? 1.0 : (horiz == HORIZON_SWING) ? 2.5 : g_positions[i].trail_atr_mult','elapsed_sec >= 3600 && !g_positions[i].be_activated','PositionIntradaySessionStatus(g_positions[i].opened,now_t,']:assert token in P
    timer=P.split('void PositionManagerTick(',1)[1]
    assert 'cfg.trail_mode' not in timer
    assert 'cfg.session_end_hour' not in timer
