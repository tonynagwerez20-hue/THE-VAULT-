"""One-terminal external-context launcher. Never launches MT5 or sends orders.

--check imports dependencies and validates paths only; no provider requests,
locks, output publication, package installation or child service startup.
"""
from __future__ import annotations
import argparse
import importlib
import os
from pathlib import Path
import sys

class ServiceLock:
    """OS-owned byte lock: automatically released on process exit, no stale PID trust."""
    def __init__(self, folder):
        self.path = Path(folder) / '.amigo-external-service.lock'
        self.file = None
    def __enter__(self):
        import msvcrt
        self.file = self.path.open('a+b')
        try:
            self.file.seek(0,2)
            if self.file.tell()==0:
                self.file.write(b'0'); self.file.flush()
            self.file.seek(0)
            msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            self.file.close(); self.file=None
            raise RuntimeError('Another AMIGO external-service launcher holds this Files folder, or locking failed.') from exc
        return self
    def __exit__(self,*args):
        import msvcrt
        if self.file:
            try:
                self.file.seek(0); msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            finally:
                self.file.close(); self.file=None

def candidate_folders():
    base=Path(os.environ.get('APPDATA',''))/'MetaQuotes'/'Terminal'
    return sorted(p.resolve() for p in base.glob('*/MQL5/Files') if p.is_dir())

def choose_folder(explicit, check):
    if explicit:
        folder=Path(explicit).expanduser().resolve()
    else:
        if check or not sys.stdin.isatty():
            raise ValueError('Specify --files "full path to the intended terminal MQL5\\Files folder".')
        choices=candidate_folders()
        print('Select the intended terminal Files folder. No terminal will be launched:')
        for i,p in enumerate(choices,1): print(f'  {i}: {p}')
        value=input('Folder number, or paste its full path: ').strip().strip('"')
        if not value: raise ValueError('No Files folder selected.')
        folder=choices[int(value)-1] if value.isdigit() and 1<=int(value)<=len(choices) else Path(value).expanduser().resolve()
    if not folder.is_dir(): raise ValueError(f'Files folder does not exist: {folder}')
    return folder

def preflight(folder):
    service=importlib.import_module('run_external_service')
    # Imports are local only: no main(), provider fetch, account or terminal API.
    if not callable(getattr(service,'main',None)): raise RuntimeError('External service entry point missing.')
    print(f'Python: {sys.executable}')
    print(f'Service: {Path(service.__file__).resolve()}')
    print(f'Market input: {folder / "Amigo_mkt_out.txt"}')
    print(f'Context output: {folder / "Amigo_ext_in.txt"}')
    print('NEWS provider supported; options scoring disabled; CFTC provenance unverified.')
    print('Legacy MGLE placeholder is NOT started and is not a current AMIGO dependency.')
    if not (folder/'Amigo_mkt_out.txt').exists():
        print('WAITING: market snapshot absent. No broker prices or ATR will be fabricated.')
    return service

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--files',help='One intended terminal MQL5/Files folder (no account access)')
    parser.add_argument('--check',action='store_true',help='Offline preflight only; no service started')
    args=parser.parse_args(argv)
    try:
        folder=choose_folder(args.files,args.check)
        service=preflight(folder)
        if args.check:
            print('CHECK PASSED: dependencies and paths only; provider connectivity NOT tested.')
            return 0
        with ServiceLock(folder):
            print('Starting external context only. Ctrl+C stops it. This does not enable trading.',flush=True)
            previous=sys.argv
            try:
                sys.argv=[str(Path(service.__file__)), '--mkt',str(folder/'Amigo_mkt_out.txt'),
                          '--out',str(folder/'Amigo_ext_in.txt'),'--interval','5']
                service.main()
            finally: sys.argv=previous
        return 0
    except KeyboardInterrupt:
        print('Stopped.'); return 0
    except (OSError,ValueError,RuntimeError,ImportError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        print('No packages installed automatically. Resolve the reported path/dependency and retry.',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
