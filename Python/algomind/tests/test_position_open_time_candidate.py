"""Registration clock/identity source contract; no native position lookup."""
from pathlib import Path
S=(Path(__file__).resolve().parents[3]/'MQL5/Include/Position Manager.mqh').read_text(encoding='utf-8-sig')

def test_broker_open_time_is_checked_before_state_allocation_and_persisted():
    register=S.split('void PositionManagerRegister(',1)[1].split('void PositionManagerRemove(',1)[0]
    clock=register.split('datetime registration_now=TimeCurrent();',1)[1].split('if(!MathIsValidNumber(cfg.partial_rr)',1)[0]
    assert 'if(!cfg.shadow_only)' in clock
    for field in ('POSITION_IDENTIFIER','POSITION_MAGIC','POSITION_TYPE','POSITION_TIME','POSITION_SYMBOL'):
        assert field in clock
    for condition in ('(ulong)identifier!=pid','(ulong)magic!=cfg.magic_number','symbol!=cfg.symbol','broker_opened<=0','broker_opened>(long)registration_now'):
        assert condition in clock
    assert 'opened=(datetime)broker_opened;' in clock
    assert register.index('opened=(datetime)broker_opened;')<register.index('ArrayResize(g_positions')
    assert 'g_positions[n].opened                = opened;' in register
    assert 'datetime opened=registration_now;' in clock
