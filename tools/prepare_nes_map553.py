# SPDX-License-Identifier: MIT
"""Enqueue one immutable map behind a newly published bulk with a reserved credit."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(arm,out):
    assert sha(arm/'obj-nes-100/firmware.stm')=='7a2797ec1d36d12787e1a8d64365d204ec31d0b3147b7ed5344c3641789d2ce4'
    out.mkdir(parents=True,exist_ok=False)
    name='nes_plan_service200.h'
    s=once((arm/name).read_text(),'bool nes_plan200_progress(struct nes_plan200 *,bool);',
           '''enum nes_progress553 {NES_ORDINARY553, NES_FINAL553, NES_MAP553};
bool nes_plan200_progress(struct nes_plan200 *,enum nes_progress553);''')
    (out/name).write_text(s,newline='\n')
    name='nes_plan_service200.c'
    s=once((arm/name).read_text(),'p->bulk_until=p->window->sent;\n   if(phase==NES_PLAN215_FINISH&&!complete485(p))return false;',
           'p->bulk_until=p->window->sent;')
    s=once(s,'nes_plan200_progress(struct nes_plan200 *p,bool finish)','nes_plan200_progress(struct nes_plan200 *p,enum nes_progress553 mode)')
    s=once(s,'if(!finish && !(flags&4))return complete485(p);','''if(flags&4){
   /* A repeat was already checked and drained inside poll. Only a new
    * descriptor can leave bulk_pending set here. A map may take one of
    * two free queue slots; its later ACK never substitutes for bulk_until. */
   if(mode==NES_MAP553 && p->bulk_pending &&
      (uint16_t)(p->window->sent-p->window->retired)<=2)return true;
   if(!complete485(p))return false;
  }else if(mode!=NES_FINAL553)return complete485(p);''')
    (out/name).write_text(s,newline='\n')
    name='nes_native_sink165.c'
    s=once((arm/name).read_text(),'!nes_plan200_progress(s->plan,op==3)',
           '!nes_plan200_progress(s->plan,op==3?NES_FINAL553:section==2&&op==2?NES_MAP553:NES_ORDINARY553)')
    (out/name).write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    prepare(a.arm,a.out)
