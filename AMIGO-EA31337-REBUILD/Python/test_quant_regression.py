import math
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'AMIGO_BASELINE/Python'))
from algomind.risk_controller import RiskController, interpolate_risk_curve
from backtest_engine import RiskManager, BacktestEngine, TrendStrategy, MeanReversionStrategy
from tib_generator import TIBGenerator

SPEC=dict(trade_tick_size=.01,trade_tick_value_loss=1.,volume_min=.01,
          volume_max=100.,volume_step=.01,commission_per_lot_roundturn=0.,
          slippage_price=0.,swap_long_per_lot_day=0.,swap_short_per_lot_day=0.,day_offset_seconds=0)

def test_sizing_uses_tick_units():
    assert RiskManager().calculate_position_size(2000,1995,SPEC)==.1

@pytest.mark.parametrize('missing', ['trade_tick_size','trade_tick_value_loss','volume_min','volume_max','volume_step'])
def test_missing_metadata_blocks(missing):
    spec=dict(SPEC);del spec[missing]
    assert RiskManager().calculate_position_size(2000,1995,spec)==0

def test_broker_max_and_step_floor():
    spec=dict(SPEC,volume_max=.03)
    assert RiskManager().calculate_position_size(2000,1995,spec)==.03
    assert RiskManager().calculate_position_size(2000,1997,SPEC)==.16

def test_unsafe_minimum_lot_blocked():
    assert RiskManager(10).calculate_position_size(2000,1995,SPEC)==0

def test_no_drawdown_throttle():
    r=RiskController(1000).evaluate(960,960,1)
    assert r.effective_risk_percent==r.base_risk_percent==.5

def test_first_mve_and_normal():
    threshold=RiskController.calculate_minimum_viable_equity(10,1.5,5)
    assert threshold==pytest.approx(276.393202250021)
    assert threshold*interpolate_risk_curve(threshold)/100*5>=10
    lower=threshold-.00001
    assert lower*interpolate_risk_curve(lower)/100*5<10
    assert RiskController.calculate_normal_equity(10)==pytest.approx(2000)

@pytest.mark.parametrize('x',[float('nan'),float('inf'),0,-1])
def test_bad_equity_blocks(x):
    assert not RiskController(1000).evaluate(x,1000,1).trade_allowed

def test_daily_lock():
    assert not RiskController(1000).evaluate(1000,1000,1,daily_locked=True).trade_allowed

def test_tib_single_ownership_and_flat_ticks():
    gen=TIBGenerator(2);bars=[]
    for n,price in enumerate([100,101,102,102,101,100]):
        bar=gen.process_tick(dict(bid=price,ask=price+1,time=1+n/1000,time_msc=1000+n))
        if bar:bars.append(bar)
    assert [b['tick_count'] for b in bars]==[3,3]
    assert [b['imbalance'] for b in bars]==[2,-2]
    assert [b['open'] for b in bars]==[100,102]
    assert [b['close_msc'] for b in bars]==[1002,1005]

def test_tib_rejects_backward_timestamp():
    g=TIBGenerator(2);g.process_tick(dict(bid=100,ask=101,time=2))
    with pytest.raises(ValueError):g.process_tick(dict(bid=101,ask=102,time=1))
    assert g.current is None

def test_partial_window_no_signal():
    for strategy in (TrendStrategy(),MeanReversionStrategy()):
        strategy.update(100);strategy.update(99)
        assert strategy.generate_signal()[0]==0

def test_rsi_rising_and_flat():
    t=TrendStrategy()
    for x in range(100,120):t.update(x)
    assert t.rsi==100
    t=TrendStrategy()
    for _ in range(20):t.update(100)
    assert t.rsi==50 and t.generate_signal()[0]==0

def test_position_is_not_resolved_randomly_at_entry():
    e=BacktestEngine(symbol_info=SPEC)
    e._execute_trade(1,.6,'fixture',2000,1000)
    assert e.position is not None and not e.trades and e.balance==10000
    stop=e.position['sl_price'];lots=e.position['position_size']
    e._mark_position(stop-.5,stop-.4,2000)
    assert len(e.trades)==1 and e.trades[0]['exit_time']==2000
    assert e.trades[0]['pnl']==pytest.approx((stop-.5-2000)*lots*100)

def test_bid_ask_exit_and_costs():
    spec=dict(SPEC,commission_per_lot_roundturn=7,slippage_price=.1)
    e=BacktestEngine(symbol_info=spec)
    e._execute_trade(-1,.5,'fixture',2000,1000)
    p=e.position.copy()
    e._mark_position(p['sl_price']-.1,p['sl_price']+.2,2000)
    assert e.trades[0]['pnl']<0
    assert e.trades[0]['exit_price']==pytest.approx(p['sl_price']+.3)

def test_uncalibrated_multiple_proposals_block():
    e=BacktestEngine(symbol_info=SPEC)
    assert e._arbitrate(1,.8,'trend',1,.6,'mr')[0]==0

def test_day_rollover_explicit():
    r=RiskManager();r.daily_entries=5
    assert not r.can_trade()
    r.balance=9900;r.reset_daily()
    assert r.day_start==9900 and r.can_trade()

def test_specification_required():
    with pytest.raises(ValueError):BacktestEngine()
