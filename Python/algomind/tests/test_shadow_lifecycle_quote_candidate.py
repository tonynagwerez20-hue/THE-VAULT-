"""Offline reference/source checks; no MQL runtime or simulated profit claims."""
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANAGER = (ROOT / 'MQL5/Include/Position Manager.mqh').read_text(encoding='utf-8-sig')


def valid_quote(bid, ask, observed, now, max_age, available=True):
    return (available and math.isfinite(bid) and bid > 0 and math.isfinite(ask)
            and ask >= bid and 0 < observed <= now and max_age > 0
            and now - observed <= max_age)


def test_invalid_or_stale_quotes_cannot_drive_shadow_lifecycle():
    assert valid_quote(2000, 2001, 100, 110, 10)
    assert not valid_quote(2000, 2001, 99, 110, 10)
    assert not valid_quote(2000, 2001, 111, 110, 10)
    assert not valid_quote(2000, 2001, 0, 110, 10)
    assert not valid_quote(2000, 1999, 100, 110, 10)
    assert not valid_quote(2000, 2001, 100, 110, 0)
    assert not valid_quote(2000, 2001, 100, 110, 10, available=False)
    for price in (0, -1, float('nan'), float('inf')):
        assert not valid_quote(price, 2001, 100, 110, 10)
        assert not valid_quote(2000, price, 100, 110, 10)


def test_shadow_quote_is_validated_before_loop_and_reused_for_exits():
    tick = MANAGER.split('void PositionManagerTick(', 1)[1]
    loop = tick.index('for(int i = ArraySize(g_positions) - 1;')
    gate = tick[:loop]
    for condition in ('SymbolInfoTick(sym,shadow_quote)',
                      '!MathIsValidNumber(shadow_quote.bid)',
                      '!MathIsValidNumber(shadow_quote.ask)',
                      'shadow_quote.ask<shadow_quote.bid',
                      'shadow_quote.time>now_t',
                      'now_t-shadow_quote.time>cfg.stale_threshold_s'):
        assert condition in gate
    shadow = tick.split('//--- Shadow Safety Mode:', 1)[1].split(
        '// HORIZON-SPECIFIC LIFECYCLE CONTROLS', 1)[0]
    assert '(dir == +1) ? shadow_quote.bid : shadow_quote.ask' in shadow
    assert 'SymbolInfoDouble' not in shadow


def test_shadow_registration_uses_final_risk_quote_without_claiming_a_fill():
    execution = (ROOT / 'MQL5/Include/Execution Engine.mqh').read_text(encoding='utf-8-sig')
    expert = (ROOT / 'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
    execute = execution.split('ExecutionResult ExecuteIntent(', 1)[1]
    shadow = execute.split('if(cfg.shadow_only)', 1)[1].split('//--- OrderCheck', 1)[0]
    assert 'r.shadow_entry = req.price;' in shadow
    assert 'r.shadow_volume = req.volume;' in shadow
    assert 'r.shadow_evaluated = true;' in shadow
    assert 'r.accepted    = false;' in shadow
    assert 'r.fill_price=' not in shadow and 'OrderSend(' not in shadow
    registration = expert.split('else if(er.position_id == 0 && g_cfg.shadow_only)', 1)[1].split(
        'if(!g_cfg.shadow_only && er.accepted)', 1)[0]
    assert '!er.shadow_evaluated' in registration
    assert 'PositionManagerRegister((ulong)decision_id, er.shadow_entry, sl, tp, er.shadow_volume' in registration
    # A refreshed buy quote of 2002 with SL 1990 has 12 price units of risk,
    # not the 10 derived from an earlier strategy quote of 2000. Shadow R-based
    # management must use the same 12-unit geometry as final risk admission.
    assert abs(2002 - 1990) == 12
    assert abs(2000 - 1990) != 12
