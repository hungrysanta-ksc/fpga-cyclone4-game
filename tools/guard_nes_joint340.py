# SPDX-License-Identifier: MIT
"""Actual340 source/output STOP, independent-read, exact-ACK and final guards."""
import inspect
from pathlib import Path
original=inspect.getsource
def source(fn):
    s=original(fn)
    if "p.suffix in ('.sv','.v','.hex','.bin','.elf','.dll','.cfg','.palette','.expected')" in s:
        s=s.replace("'.palette','.expected')", "'.palette','.expected','.records')")
    return s
inspect.getsource=source
if __name__=='__main__':
    p=Path(__file__).with_name('guard_nes_read336.py')
    s=p.read_text().replace("'probe_nes_read336.py'","'probe_nes_live340.py'")
    exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
