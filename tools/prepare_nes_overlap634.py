# SPDX-License-Identifier: MIT
"""Size the bounded receiver callback in a complete 625 ARM link."""
import argparse
import shutil
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out):
    assert sha(base/'src/obj-nes-100/firmware.stm')=='d4ea668a8a30c9dbc4b3858a51379abddb2efc3b36e35024f3c7b8531901693a'
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    p=out/'src/nes_native_runtime165.h'
    h=once(p.read_text(),'bool inside_transfer;','bool inside_transfer;uint8_t prefetch_left;')
    p.write_text(h,newline='\n')
    p=out/'src/nes_native_runtime165.c'
    s=p.read_text()
    s=once(s,'s->inside_transfer=false;s->transactions++;', '''s->inside_transfer=false;
 if(ok&&opcode==0xe1&&n>=2&&tx[1]==3)s->prefetch_left=7;
 s->transactions++;''')
    s=once(s,'static bool finish_bg549(','''static bool wait634(void *ctx,bool (*check)(void *),unsigned reason,bool progress){
 struct nes_native_runtime165 *s=ctx;
 if(s->prefetch_left&&reason==2&&!progress){
  struct nes_native165 *r=s->receiver;
  nes_native165_consumed(r);
  if(r->state!=NES_NATIVE165_COMPLETE){
   --s->prefetch_left;
   if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
  }
 }
 return nes_cost474_pause(ctx,check,reason,progress);
}
static bool finish_bg549(''')
    s=once(s,'s->transport.wait=nes_cost474_pause;','s->transport.wait=wait634;')
    s=once(s,'if(!s->sink.displayed||s->sink.last_generation!=r->generation)',
           's->prefetch_left=0;\n  if(!s->sink.displayed||s->sink.last_generation!=s->video->generation)')
    s=once(s,'s->frames++;s->generation=r->generation;','s->frames++;s->generation=s->video->generation;')
    p.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.base,a.out)
