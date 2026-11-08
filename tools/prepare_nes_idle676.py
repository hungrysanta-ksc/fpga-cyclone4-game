"""Replace map-tail fixed quiet time with one bounded checked input opportunity."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest,evidence
from nes_raw506 import once

def prepare(base,out,ending_grant=False):
    assert digest(base/'src/obj-nes-100/firmware.stm')==evidence('bg675-verification.json')['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_native_sink165.c'
    s=once(p.read_text(),'''   for(unsigned slot=0;slot<40;slot++)
    if(!s->plan->window->wait(s->plan->ctx,s->plan->guard,slot<38?0:3,false))return fail(s,5);''','''   /* The checked map receipt emptied the queue, not VRAM. Keep it empty
    * for a bounded input transaction while the SNES idle selector may DMA.
    * No timed silence, fabricated DMA completion or display credit. */
   if(!s->plan->window->wait(s->plan->ctx,s->plan->guard,4,false))return fail(s,5);''')
    p.write_text(s,newline='\n')
    if ending_grant:
        p=out/'src/nes_plan_service200.c'
        s=once(p.read_text(),"((p->ending && p->count==1 && p->buffer[4]==0x83) || bg675(p)))result|=1;",
               "(p->ending || bg675(p)))result|=1;")
        p.write_text(s,newline='\n')
    p=out/'src/nes_native_runtime165.c'
    s=once(p.read_text(),''' struct nes_native_runtime165 *s=ctx;
 if(reason==3){''',''' struct nes_native_runtime165 *s=ctx;
 if(reason==4){
  /* One STATUS and optional CRC-checked READ/restore/POP. No waiting for a
   * future capture and no new COMMIT while the old display owns its lease. */
  struct nes_native165 *r=s->receiver;
  if(!check(ctx))return false;
  if(r->state==NES_NATIVE165_COMMITTED)s->prefetch_left=7;
  nes_native165_consumed(r);
  if(s->prefetch_left && r->state!=NES_NATIVE165_COMPLETE){
   --s->prefetch_left;
   if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
  }
  return check(ctx);
 }
 if(reason==3){''')
    p.write_text(s,newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--ending-grant',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.ending_grant)
