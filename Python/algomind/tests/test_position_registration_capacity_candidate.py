"""Position storage admission contract; offline source and boundary checks."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[3]
M=(ROOT/'MQL5/Include/Position Manager.mqh').read_text(encoding='utf-8-sig')
E=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
R=(ROOT/'MQL5/Include/PositionRecovery.mqh').read_text(encoding='utf-8-sig')

def test_capacity_matches_persistent_record_limit():
    limit=int(re.search(r'#define AMIGO_STATE_MAX_POSITIONS\s+(\d+)',R).group(1))
    assert limit==64
    assert 63<limit and not 64<limit and not 65<limit
    helper=M.split('bool PositionManagerHasCapacity()',1)[1].split('void PositionManagerRegister(',1)[0]
    assert 'ArraySize(g_positions)<AMIGO_STATE_MAX_POSITIONS' in helper
    body=E.split('int OnClosedBar(',1)[1]
    assert body.index('if(!PositionManagerHasCapacity())')<body.index('ExecuteIntent(ti,')
    assert 'return RISK_OP_REJECTED;' in body.split('if(!PositionManagerHasCapacity())',1)[1].split('//--- 12) Execute',1)[0]


def test_registration_validates_derived_state_before_resizing():
    body=M.split('void PositionManagerRegister(',1)[1].split('//| Close or remove',1)[0]
    resize=body.index('ArrayResize(g_positions, n + 1)')
    for token in ('!PositionManagerHasCapacity()', 'opened<=0',
                  '!MathIsValidNumber(tp_distance)', '!MathIsValidNumber(be_trigger)',
                  'cfg.trail_mode!=TRAIL_DYNAMIC_25_PERCENT'):
        assert body.index(token)<resize
    assert 'g_positions[n].opened                = opened;' in body
    assert body.index('PositionSaveState(cfg)')>resize
