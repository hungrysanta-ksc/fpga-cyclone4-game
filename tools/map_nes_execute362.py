# SPDX-License-Identifier: MIT
"""Whole Lite from repaired358: remove host continuation359 and local CRC362."""
import inspect,sys
import map_nes_joint284 as old
from nes_host359 import apply as host
from nes_execute362 import apply
separate='--separate-crc' in sys.argv
if separate:sys.argv.remove('--separate-crc')
def patch(d):
 host(d,board=True)
 if not separate:apply(d)
if __name__=='__main__':
 s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-exec358/map01')
 s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_host359.py','nes_execute362.py','map_nes_execute362.py')")
 ns=dict(old.__dict__);ns['apply']=patch;exec(compile(s,__file__,'exec'),ns);ns['main']()
