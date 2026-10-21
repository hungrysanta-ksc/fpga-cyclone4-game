# SPDX-License-Identifier: MIT
"""Matched whole Quartus Lite map for the descriptor/receipt owner."""
import inspect
import map_nes_joint284 as old
from nes_joint287 import apply

def main():
    s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-joint286/board01')
    s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_joint287.py','map_nes_joint287.py')")
    ns=dict(old.__dict__);ns['apply']=apply;exec(compile(s,'map287','exec'),ns);ns['main']()

if __name__=='__main__':main()
