# SPDX-License-Identifier: MIT
"""Whole Lite diagnostic cancellation repair of356; not a NES common executor area claim."""
import inspect
import map_nes_joint284 as old
from nes_cancel358 import apply
def patch(d):apply(d,board=True)
if __name__=='__main__':
 s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-query356/map01')
 s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_cancel358.py','map_nes_cancel358.py')")
 ns=dict(old.__dict__);ns['apply']=patch;exec(compile(s,__file__,'exec'),ns);ns['main']()
