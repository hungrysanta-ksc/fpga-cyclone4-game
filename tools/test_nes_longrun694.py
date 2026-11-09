"""Run the actual693 linked long-session ABI with the unchanged689 timing oracle."""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Runtime

original=Runtime.call
def call(self,name,args):
    if name=='nes_runtime165_begin':
        assert args[8]==6000
        args=list(args);args[8]=0  # Selected long-only API; execute its real begin.
    return original(self,name,args)

if __name__=='__main__':
    with patch.object(Runtime,'call',call):
        runpy.run_module('test_nes_status689',run_name='__main__')
