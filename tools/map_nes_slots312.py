# SPDX-License-Identifier: MIT
"""Whole Lite MAP of the two-slot transport prerequisite, not full replacement."""
import inspect
import map_nes_joint284 as old
from nes_slots312 import apply as slots
from nes_record312 import apply as record
def apply(d):slots(d);record(d)
def main():
    s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-ingress307/board03')
    s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_slots312.py','nes_record312.py','map_nes_slots312.py')")
    ns=dict(old.__dict__);ns['apply']=apply
    exec(compile(s,'map312','exec'),ns);ns['main']()
if __name__=='__main__':main()
