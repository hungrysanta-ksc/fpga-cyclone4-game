# SPDX-License-Identifier: MIT
"""495 C/SPI/source/PSRAM/old489 SNES functional join; not physical M4 timing."""
import runpy,shutil
from pathlib import Path
from nes_status495 import ROOT,once
original=shutil.copyfile
def copy(source,dest,*args,**kw):
    r=original(source,dest,*args,**kw)
    if Path(source).resolve()==ROOT/'tests/nes-nrom447/runtime.c' and Path(dest).name=='host.c':
        p=Path(dest);s=p.read_text()
        s=once(s,'}else if(cmd==0xe0){\n  assert(n==20);',
                 '}else if(cmd==0xe0||cmd==0xeb){\n  assert(n==(cmd==0xeb?8:20));')
        p.write_text(s,encoding='utf8',newline='\n')
    return r
if __name__=='__main__':
    shutil.copyfile=copy
    try:runpy.run_path(str(ROOT/'tools/test_nes_consume491_live.py'),run_name='__main__')
    finally:shutil.copyfile=original
