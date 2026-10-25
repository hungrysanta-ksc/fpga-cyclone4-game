# SPDX-License-Identifier: MIT
"""Retain actual read/STOP/final-ACK guards on the changed338 ingress."""
from pathlib import Path

if __name__=='__main__':
    p=Path(__file__).with_name('guard_nes_read336.py')
    s=p.read_text().replace("'probe_nes_read336.py'","'probe_nes_ingress338.py'")
    exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
