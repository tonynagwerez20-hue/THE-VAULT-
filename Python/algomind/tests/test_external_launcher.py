"""Offline tests: no provider requests, terminal startup or account access."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from unittest.mock import patch
from types import SimpleNamespace
import pytest
import launch_external_services as launcher
import run_external_service as service


def test_check_has_no_service_or_lock_side_effects(tmp_path):
    module=SimpleNamespace(__file__=str(Path(service.__file__)),main=lambda:pytest.fail('service started'))
    with patch.object(launcher.importlib,'import_module',return_value=module),patch.object(launcher,'ServiceLock',side_effect=AssertionError('lock opened')):
        assert launcher.main(['--check','--files',str(tmp_path)])==0
    assert list(tmp_path.iterdir())==[]

def test_absent_directory_fails(tmp_path):
    assert launcher.main(['--check','--files',str(tmp_path/'absent')])==1

def test_dependency_failure_reported(tmp_path):
    with patch.object(launcher.importlib,'import_module',side_effect=ImportError('missing dependency')):
        assert launcher.main(['--check','--files',str(tmp_path)])==1

def test_second_launcher_cannot_hold_same_lock(tmp_path):
    with launcher.ServiceLock(tmp_path):
        with pytest.raises(RuntimeError):
            with launcher.ServiceLock(tmp_path):pass
    with launcher.ServiceLock(tmp_path):pass

def test_foreground_service_bound_to_exact_folder(tmp_path):
    calls=[]
    module=SimpleNamespace(__file__=str(Path(service.__file__)),main=lambda:calls.append(list(sys.argv)))
    before=list(sys.argv)
    with patch.object(launcher.importlib,'import_module',return_value=module):
        assert launcher.main(['--files',str(tmp_path)])==0
    assert calls==[[str(Path(service.__file__)),'--mkt',str(tmp_path/'Amigo_mkt_out.txt'),'--out',str(tmp_path/'Amigo_ext_in.txt'),'--interval','5']]
    assert sys.argv==before

@pytest.mark.parametrize('extra',[['--out2','second'],['--interval','nan'],['--interval','0'],['--interval','inf']])
def test_unsafe_service_arguments_rejected_before_provider_call(extra):
    with patch.object(sys,'argv',['service','--mkt','mock','--out','mockout',*extra]),patch.object(service,'build_context',side_effect=AssertionError('provider called')):
        with pytest.raises(SystemExit) as error:service.main()
    assert error.value.code==2
