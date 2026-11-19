"""Read-only HistData adapter and bounded-memory AMIGO prototype research replay."""
import argparse, hashlib, json, math, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
REPO=Path(r'E:\AMIGO-EA31337-REBUILD')
sys.path.insert(0,str(REPO/'Python'))
from backtest_engine import BacktestEngine

class EquityAccumulator:
    def __init__(self, initial):
        self.last=self.peak=initial;self.maximum_drawdown=0.;self.count=0
    def append(self,value):
        self.last=value;self.peak=max(self.peak,value)
        self.maximum_drawdown=max(self.maximum_drawdown,(self.peak-value)/self.peak if self.peak>0 else 0.)
        self.count+=1

class ResearchEngine(BacktestEngine):
    def __init__(self,equity,spec):
        super().__init__('XAUUSD_RESEARCH',equity,spec)
        self.equity_curve=EquityAccumulator(equity)
    def _generate_report(self):
        # Entry can occur after the parent's per-tick mark; value that final position explicitly.
        equity=self.balance
        if self.position and hasattr(self,'last_quote'):
            p=self.position;bid,ask=self.last_quote
            mark=bid if p['direction']==1 else ask
            equity+=(mark-p['entry_price'])*p['direction']*p['position_size']*self.symbol_info['trade_tick_value_loss']/self.symbol_info['trade_tick_size']
            equity-=p['position_size']*self.symbol_info['commission_per_lot_roundturn']
        final_drawdown=(self.equity_curve.peak-equity)/self.equity_curve.peak if self.equity_curve.peak>0 else 0.
        closed=sum(t['pnl'] for t in self.trades)
        return dict(initial_equity=self.initial_balance,final_balance=self.balance,final_marked_equity=equity,
            net_equity_change=equity-self.initial_balance,closed_trades=len(self.trades),
            closed_trade_pnl=closed,separate_cash_adjustments=self.balance-self.initial_balance-closed,
            unrealized_after_reserved_commission=equity-self.balance,
            max_drawdown_pct=100*max(self.equity_curve.maximum_drawdown,final_drawdown),open_position=self.position,
            ticks_processed=self.equity_curve.count,scope='Existing single-position Python prototype; not native, multi-horizon or hedging parity',
            assumptions=self.symbol_info)
    def _mark_position(self,bid,ask,timestamp):
        self.last_quote=(bid,ask)
        return super()._mark_position(bid,ask,timestamp)

def bounds(value):
    value=datetime.fromisoformat(value)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def selected_files(manifest,start,end):
    # UTC bounds mapped to provider's documented fixed EST, not a guessed DST correction.
    a=pd.Timestamp(start)-pd.Timedelta(hours=5)
    b=pd.Timestamp(end)-pd.Timedelta(milliseconds=1,hours=5)
    needed=set(str(x) for x in pd.period_range(a.tz_localize(None),b.tz_localize(None),freq='M'))
    available={f['month']:f for f in manifest['accepted']}
    missing=needed-set(available)
    if missing:raise ValueError('Excluded or unavailable months: '+', '.join(sorted(missing)))
    return [available[m] for m in sorted(needed)]

def ticks(files,start,end):
    lo=int(start.timestamp()*1000);hi=int(end.timestamp()*1000);previous=None
    for entry in files:
        path=Path(entry['path']);h=hashlib.sha256()
        with path.open('rb') as f:
            while chunk:=f.read(1024*1024):h.update(chunk)
        if h.hexdigest()!=entry['sha256']:raise ValueError('Source checksum changed: '+str(path))
        with zipfile.ZipFile(path) as z:
            name=next(n for n in z.namelist() if n.lower().endswith('.csv'))
            with z.open(name) as f:
                for chunk in pd.read_csv(f,header=None,names=['stamp','bid','ask','volume'],dtype={'stamp':str},chunksize=200000):
                    time=pd.to_datetime(chunk.stamp,format='%Y%m%d %H%M%S%f',errors='raise')+pd.Timedelta(hours=5)
                    ms=time.to_numpy(dtype='datetime64[ms]').astype('int64')
                    mask=(ms>=lo)&(ms<hi)
                    for ts,bid,ask in zip(ms[mask],chunk.bid.to_numpy()[mask],chunk.ask.to_numpy()[mask]):
                        if not math.isfinite(bid) or not math.isfinite(ask) or not 0<bid<=ask or (previous is not None and ts<previous):
                            raise ValueError('Invalid chronological quote stream')
                        previous=int(ts)
                        yield dict(time_msc=int(ts),time=int(ts)//1000,bid=float(bid),ask=float(ask))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--start',required=True,help='UTC ISO date/time')
    p.add_argument('--end',required=True,help='UTC exclusive end')
    p.add_argument('--output',required=True)
    args=p.parse_args();start,end=bounds(args.start),bounds(args.end)
    if start>=end:raise ValueError('End must follow start')
    manifest=json.loads((HERE/'dataset.json').read_text())
    for path,expected in manifest['source_hashes'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise ValueError('Prototype source changed: '+path)
    scenario=json.loads((HERE/'scenario.json').read_text())
    selected=selected_files(manifest,start,end)
    engines=[ResearchEngine(e,scenario['specification']) for e in scenario['equities_usd']]
    # Existing strategy implementations consume each identical source quote once per account.
    # Shared bounded batches avoid loading the entire history or storing per-tick equity arrays.
    batch=[];count=0
    import contextlib,io
    def replay_batch():
        for engine in engines:
            with contextlib.redirect_stdout(io.StringIO()):engine.run_backtest(start,end,ticks=batch)
    for tick in ticks(selected,start,end):
        batch.append(tick);count+=1
        if len(batch)>=10000:replay_batch();batch.clear()
    if batch:replay_batch()
    if not count:raise ValueError('No quotes in requested interval')
    reports=[e._generate_report() for e in engines]
    result=dict(start_utc=start.isoformat(),end_utc_exclusive=end.isoformat(),input_ticks=count,
        scope='Diagnostic prototype replay only; fixed 0.5% risk, one position, no native horizon or hedging/margin parity',
        scenario=scenario,source_months=[f['month'] for f in selected],accounts=reports)
    dest=Path(args.output)
    if dest.exists():raise FileExistsError('Refusing to overwrite existing results')
    dest.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(dict(input_ticks=count,accounts=len(reports),closed_trades=[r['closed_trades'] for r in reports],output=str(dest)),indent=2))

if __name__=='__main__':main()
