# SPDX-License-Identifier: MIT
"""One whole Quartus Lite MAP of the shared host/validator identity owner."""
import inspect
import map_nes_joint284 as old
from nes_joint286 import apply


def main():
    source=inspect.getsource(old.main).replace("probes/nes-joint280/board01","probes/nes-joint284/board02")
    source=source.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_joint286.py','map_nes_joint286.py')")
    ns=dict(old.__dict__);ns['apply']=apply;exec(compile(source,'map286','exec'),ns);ns['main']()


if __name__=='__main__':main()
