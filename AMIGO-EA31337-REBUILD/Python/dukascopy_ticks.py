"""Resumable public XAUUSD BI5 acquisition, with explicit missing-hour evidence.
No generated ticks, account access, paid S3 requests, or package installation.
"""
import argparse
import hashlib
import json
import lzma
import struct
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

def decode(data):
    raw=lzma.decompress(data) if data else b''
    if len(raw)%20: raise ValueError('Truncated BI5 record')
    previous=-1
    for ms,ask,bid,av,bv in struct.iter_unpack('>IIIff',raw):
        if ms<previous or ms>=3600000 or bid<=0 or ask<bid:
            raise ValueError('Invalid/unordered BI5 quote')
        previous=ms
        yield ms,bid/1000.,ask/1000.

def fetch(hour,cache):
    relative=f'XAUUSD/{hour.year}/{hour.month-1:02}/{hour.day:02}/{hour.hour:02}h_ticks.bi5'
    url='https://datafeed.dukascopy.com/datafeed/'+relative
    path=cache/relative
    try:
        if path.exists(): data=path.read_bytes()
        else:
            with urllib.request.urlopen(url,timeout=20) as response: data=response.read()
            # Validate before publishing a cache file.
            list(decode(data))
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.part');temp.write_bytes(data);temp.replace(path)
        count=sum(1 for _ in decode(data))
        return dict(hour=hour.isoformat(),url=url,status='ticks' if count else 'empty',
                    ticks=count,sha256=hashlib.sha256(data).hexdigest())
    except Exception as error:
        return dict(hour=hour.isoformat(),url=url,status='unavailable',error=str(error))

def acquire(start,end,cache,manifest):
    manifest.parent.mkdir(parents=True,exist_ok=True)
    # Probe a weekday near each boundary before attempting 87,000+ requests.
    probes=[]
    for point in (start,end-timedelta(days=1)):
        while point.weekday()>=5: point-=timedelta(days=1)
        probes.append(fetch(point.replace(hour=12),cache))
    state=dict(source='Dukascopy public BI5',symbol='XAUUSD',start=start.isoformat(),
               end_exclusive=end.isoformat(),complete=False,probes=probes)
    if any(p['status']!='ticks' for p in probes):
        state['blocker']='Boundary coverage unavailable; full download and backtest not started'
        manifest.write_text(json.dumps(state,indent=2));return state
    journal=manifest.with_suffix('.jsonl')
    hour=start;unavailable=empty=count=0
    with journal.open('a',encoding='utf-8') as f:
        while hour<end:
            item=fetch(hour,cache);f.write(json.dumps(item)+'\n');f.flush()
            if item['status']=='unavailable':
                unavailable+=1
                # Stop on provider/transport failure instead of hammering it.
                state['blocker']=item;break
            empty+=item['status']=='empty';count+=item['ticks']
            hour+=timedelta(hours=1)
            if hour.hour==0: print(hour.isoformat(),count,flush=True)
    state.update(downloaded_through_exclusive=hour.isoformat(),ticks=count,empty_hours=empty,
                 unavailable_hours=unavailable,complete=hour==end and unavailable==0,
                 limitation='Empty hours require trading-calendar reconciliation before economic acceptance')
    manifest.write_text(json.dumps(state,indent=2));return state

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--start',required=True);p.add_argument('--end',required=True)
    p.add_argument('--cache',required=True);p.add_argument('--manifest',required=True);a=p.parse_args()
    start=datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc)
    end=datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc)
    if end<=start: p.error('end must follow start')
    result=acquire(start,end,Path(a.cache),Path(a.manifest))
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['complete'] else 2)
