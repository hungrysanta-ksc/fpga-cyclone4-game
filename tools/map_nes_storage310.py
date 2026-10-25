# SPDX-License-Identifier: MIT
"""Whole Lite MAP of the stored-credit/shared-reader candidate."""
import inspect
import map_nes_joint284 as old
from nes_storage310 import apply

def main():
    s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-ingress307/board03')
    s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_storage310.py','map_nes_storage310.py','nes_joint303.py')")
    ns=dict(old.__dict__);ns['apply']=apply
    exec(compile(s,'map310','exec'),ns);ns['main']()
if __name__=='__main__':main()
