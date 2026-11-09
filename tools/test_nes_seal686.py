"""Retain685 CPU oracle and observe actual reason3 SEAL-owned input entry."""
import inspect,runpy
import test_nes_receive682 as receive
from nes_raw506 import once

if __name__=='__main__':
    source=once(inspect.getsource(receive.observe),'not in (0,1,2,4)','not in (0,1,2,3,4)')
    ns=dict(vars(receive));exec(source,ns);receive.observe=ns['observe']
    runpy.run_module('test_nes_complete685',run_name='__main__')
