# SPDX-License-Identifier: MIT
import inspect
import map_nes_joint284 as old
from nes_obj362 import apply
from nes_query356 import apply as query
from nes_cancel358 import apply as cancel
from nes_execute362 import apply as common
import sys
joint='--joint' in sys.argv
if joint:sys.argv.remove('--joint')
def patch(d):
 apply(d,board=True)
 if joint:query(d);cancel(d,board=True);common(d)
if __name__=='__main__':
 s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-hint361/map02')
 s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_obj362.py','map_nes_obj362.py')")
 ns=dict(old.__dict__);ns['apply']=patch;exec(compile(s,__file__,'exec'),ns);ns['main']()
