"""Timeframe volatility oracle/source wiring checks, not native MQL execution."""
from pathlib import Path
import math
import pytest
ROOT=Path(__file__).resolve().parents[3]
STRUCTURE=(ROOT/'MQL5/Include/Structure Engine.mqh').read_text(encoding='utf-8-sig')


def atr(rows, period):
    if period <= 0 or len(rows) <= period:
        return None
    ranges=[]
    for i in range(period):
        high,low,_=rows[i]
        previous_close=rows[i+1][2]
        value=max(high-low, abs(high-previous_close), abs(low-previous_close))
        if not all(map(math.isfinite, (high,low,previous_close,value))) or value<0:
            return None
        ranges.append(value)
    result=math.fsum(ranges)/period
    return result if result>0 else None


def test_gap_true_range_uses_older_close_not_forming_bar():
    # Ranges: 12 (gap from 100), then 4; independently expected mean = 8.
    assert atr([(112,108,110),(102,98,100),(101,99,100)],2)==8


def test_different_timeframes_do_not_share_execution_volatility():
    assert atr([(101,99,100)]*15,14)==2
    assert atr([(120,80,100)]*15,14)==40


@pytest.mark.parametrize('rows,period', [([],14), ([(101,99,100)]*14,14),
    ([(100,100,100)]*15,14), ([(101,99,100)]*15,0),
    ([(float('inf'),99,100)]*15,14)])
def test_unavailable_or_invalid_volatility_is_rejected(rows,period):
    assert atr(rows,period) is None


def test_all_seven_timeframes_use_validated_own_snapshot():
    reader=STRUCTURE.split('bool TryEvaluateClosedStructure(',1)[1].split('struct TopDownContext',1)[0]
    assert 'const int atr_period' in reader
    assert reader.index('ValidateClosedRateSequence(') < reader.index('double atr=0.0;')
    assert 'if(got<=atr_period) return false;' in reader
    assert 'rates[i+1].close' in reader
    assert 'atr+=tr/(double)atr_period;' in reader
    assert 'ComputeATR14(' not in reader
    assert 'iATR(' not in reader
    topdown=STRUCTURE.split('bool EvaluateTopDownContext(',1)[1]
    for frame in ('D1','H4','H1','M30','M15','M5','M1'):
        assert f'TryEvaluateClosedStructure(symbol,PERIOD_{frame},atr_period,asof_boundary,' in topdown
    assert 'm5_atr' not in topdown
    expert=(ROOT/'MQL5/Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
    assert 'EvaluateTopDownContext(g_symbol,g_cfg.atr_period,decision_boundary,td)' in expert
