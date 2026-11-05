"""Double only the guarded terminal wait after an empty plan-status response."""
import argparse
from pathlib import Path
import shutil

from check_nes_wire600 import ROOT, pin, read
from nes_raw506 import once


def prepare(base, out):
    pin(base/'src/obj-nes-100/firmware.stm',
        read(ROOT/'analysis/planner607-builds.json')['recent577']['firmware'])
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    source=out/'src/nes_plan_service200.c'
    text=source.read_text()
    old='  }else if(mode!=NES_FINAL553)return complete485(p);'
    new='''  }else{
   if(mode!=NES_FINAL553)return complete485(p);
   /* No ordinary packet remains. Keep checking STOP while waiting for
    * the next producer response. Never defer a visible bulk descriptor. */
   if(!wait485(p))return false;
  }'''
    source.write_bytes(once(text,old,new).encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','out'):
        p.add_argument(k,type=Path)
    args=p.parse_args();prepare(args.base,args.out)
