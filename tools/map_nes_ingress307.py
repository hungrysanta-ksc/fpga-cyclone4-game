# SPDX-License-Identifier: MIT
"""Whole Lite MAP, pinned305 plus actual common ingress/manifest replacement."""
import inspect
import map_nes_joint284 as old
from nes_ingress307 import apply

def main():
    s=inspect.getsource(old.main).replace('probes/nes-joint280/board01','probes/nes-record305/board02')
    s=s.replace("('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py')","('nes_ingress307.py','map_nes_ingress307.py')")
    ns=dict(old.__dict__);ns['apply']=apply
    exec(compile(s,'map307','exec'),ns);ns['main']()
if __name__=='__main__':main()
