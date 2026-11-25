from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[3]/'MQL5'
def test_exact_seven_timeframe_inputs_match_fixed_analysis_reads():
    e=(ROOT/'Experts/AMIGO.mq5').read_text(encoding='utf-8-sig')
    s=(ROOT/'Include/Structure Engine.mqh').read_text(encoding='utf-8-sig')
    pairs=re.findall(r'input ENUM_TIMEFRAMES (\w+)\s*=\s*(PERIOD_\w+)',e)
    expected=['PERIOD_D1','PERIOD_H4','PERIOD_H1','PERIOD_M30','PERIOD_M15','PERIOD_M5','PERIOD_M1']
    assert [tf for _,tf in pairs]==expected
    for name,tf in pairs:
        assert name+'!='+tf in e
        assert 'TryEvaluateClosedStructure(symbol,'+tf+',' in s
    assert 'InpTFM1' not in e
    assert 'g_cfg.tf_m1               = InpTFExec;' in e
