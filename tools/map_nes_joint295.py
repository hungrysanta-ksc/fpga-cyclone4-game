# SPDX-License-Identifier: MIT
"""Whole Lite MAP of the shared receipt endpoint, against pinned NES287."""
import inspect
import map_nes_joint284 as old
from nes_close295 import apply


def main():
    s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-joint287/board01')
    s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_close295.py','map_nes_joint295.py')")
    ns=dict(old.__dict__);ns['apply']=apply
    exec(compile(s,'map290','exec'),ns);ns['main']()


if __name__=='__main__':main()
