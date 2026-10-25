# SPDX-License-Identifier: MIT
import inspect
import map_nes_joint284 as old
from nes_rows363 import apply as rows
def patch(d):rows(d,board=True)
if __name__=='__main__':
 s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-execute362/objmap01')
 s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_rows363.py','map_nes_rows363.py')")
 ns=dict(old.__dict__);ns['apply']=patch;exec(compile(s,__file__,'exec'),ns);ns['main']()
