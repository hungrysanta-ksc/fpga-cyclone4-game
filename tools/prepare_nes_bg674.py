"""Send two validated warm BG records before waiting for OBJ/END on MMC666."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest,evidence
from nes_raw506 import once


def prepare(base,out):
    assert digest(base/'src/obj-nes-100/firmware.stm')==evidence('trial666-package.json')['firmware_SHA256']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_plan_service200.c'
    s=once(p.read_text(),'''  if(!p->early)return nes_plan549_first(p);
  /* Confirmed BG records''','''  if(!p->early)return nes_plan549_first(p);
  /* Two already validated BG records need not wait for OBJ or END.
   * Reuse the guarded E8/E9 handoff, its owned buffer and STOP checks.
   * Cold frames and the first BG publication keep their original path;
   * no frame number, beam phase, new storage or early display ACK. */
  if(p->bank_history==2 && p->count==2 && p->obj_start==p->bytes)
   return flush(p);
  /* Confirmed BG records''')
    p.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.base,a.out)
