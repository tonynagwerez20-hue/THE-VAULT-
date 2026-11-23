"""Offline verification: arithmetic fixtures are not market/performance data.
No MT5 import, account access, order calls, or production edits.
"""
import ast, hashlib, json, math, sys
from pathlib import Path
from typing import Tuple
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
import numpy as np

ROOT = Path(r'E:\AMIGO-EA31337-REBUILD')
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'AMIGO_BASELINE/Python'))
from algomind.risk_controller import RiskController, interpolate_risk_curve

# Load only reviewed class definitions, excluding imports and executable main.
p = ROOT / 'Python/backtest_engine.py'
tree = ast.parse(p.read_text(encoding='utf-8-sig'))
selected = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in
            ('RiskManager', 'TrendStrategy', 'MeanReversionStrategy')]
ns = {'np': np, 'Tuple': Tuple, 'MAX_DAILY_ENTRIES': 5, 'math': math, 'Decimal': Decimal, 'ROUND_FLOOR': ROUND_FLOOR, 'ROUND_CEILING': ROUND_CEILING}
exec(compile(ast.Module(body=selected, type_ignores=[]), str(p), 'exec'), ns)
results = []
def check(name, observed, expected, ok):
    results.append(dict(check=name, observed=observed, expected=expected,
                        status='PASS' if ok else 'FAIL'))

rm = ns['RiskManager']()
spec = dict(volume_min=.01, volume_step=.01, volume_max=100,
            trade_tick_size=.01, trade_tick_value_loss=1.)
v = rm.calculate_position_size(2000, 1995, spec)
cash_risk = v * 5 / .01
check('Q02 dimensionally correct sizing', dict(lots=v, stop_risk=cash_risk),
      dict(lots=.1, stop_risk=50.), math.isclose(v, .1))
v2 = rm.calculate_position_size(2000, 1995, {})
check('Q02 absent metadata fails closed', v2, 0., v2 == 0.)
rc = RiskController(1000.)
r = rc.evaluate(960., 960., 1.)
check('Q03 no drawdown throttle', r.effective_risk_percent, r.base_risk_percent,
      r.effective_risk_percent == r.base_risk_percent)
stop = rc.evaluate(960., 960., 1., daily_locked=True)
check('daily lock blocks Python mirror', stop.trade_allowed, False, not stop.trade_allowed)
bad = rc.evaluate(float('nan'), 960., 1.)
check('nonfinite equity rejected', bad.trade_allowed, False, not bad.trade_allowed)
# Fixed D=5, L_min=10, approved piecewise risk curve. First crossing
# occurs in [250,500], verified by the analytical quadratic and bisection.
lo, hi = 250., 500.
for _ in range(80):
    mid = (lo + hi) / 2
    if mid * interpolate_risk_curve(mid) / 100 * 5 >= 10: hi = mid
    else: lo = mid
actual = RiskController.calculate_minimum_viable_equity(10., interpolate_risk_curve(10.), 5.)
check('Q04 first feasible equity with fixed D=5', actual, hi, math.isclose(actual, hi, abs_tol=.01))
check('normal threshold E=2000 for L_min=10',
      2000 * interpolate_risk_curve(2000) / 100, 10.,
      math.isclose(2000 * interpolate_risk_curve(2000) / 100, 10.))
# These are unit-test numbers, not a fabricated historical price series.
mr = ns['MeanReversionStrategy']()
mr.update(100.); mr.update(99.)
check('Q06 insufficient lookback returns NO_TRADE', mr.generate_signal()[0], 0,
      mr.generate_signal()[0] == 0)
check('Q01 outcome must use subsequent prices',
      'np.random.random()' in ast.get_source_segment(p.read_text(encoding='utf-8-sig'),
        next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BacktestEngine')),
      False, 'np.random.random()' not in p.read_text(encoding='utf-8-sig'))
syntax_files = sorted(q for q in (ROOT/'Python').glob('*.py') if q.is_file())
for q in syntax_files:
    ast.parse(q.read_text(encoding='utf-8-sig'))
check('rebuild Python syntax', len(syntax_files), len(syntax_files), True)
payload = dict(scope='Offline arithmetic and source checks; no native MQL runtime parity',
               results=results, passed=sum(x['status']=='PASS' for x in results),
               failed=sum(x['status']=='FAIL' for x in results))
(OUT/'verification_results.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
print(json.dumps(payload, indent=2))
paths = list((ROOT/'ARCHITECTURE').glob('*.mq*')) + list((ROOT/'Python').glob('*.py'))
paths += [ROOT/'AMIGO_BASELINE/Python/algomind/risk_controller.py',
          ROOT/'AMIGO_BASELINE/Python/algomind/account_execution.py']
paths += [ROOT/'AMIGO_BASELINE/MQL5/Include'/s for s in ['RiskController.mqh',
          'Risk Engine.mqh', 'Execution Engine.mqh', 'Regime Engine.mqh',
          'Contracts header.mqh', 'Strategy Engine.mqh', 'Market Snapshot Builder.mqh']]
(OUT/'source_hashes.json').write_text(json.dumps({str(q): hashlib.sha256(q.read_bytes()).hexdigest()
    for q in paths if q.is_file()}, indent=2), encoding='utf-8')
