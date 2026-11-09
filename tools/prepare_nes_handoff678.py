"""Use one real input transaction at a checked map-to-ready-tile handoff."""
import argparse,shutil
from pathlib import Path
from check_nes_fault641 import digest,evidence
from nes_raw506 import once

def prepare(base,out,multi=False,credit=False):
    assert digest(base/'src/obj-nes-100/firmware.stm')==evidence('map677-verification.json')['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_plan_service200.c'
    s=once(p.read_text(),'''   if(!complete485(p)||!nes_sink195_submit(p->sink,d))return fail(p,5);''','''   if(!complete485(p))return false;
   /* A new ready tile follows the accepted warm map run. Retain its checked
    * descriptor on this stack, retire the real map queue, and service one
    * bounded input transaction. SNES still owns DMA selection and STOP/new
    * packet priority; neither receipt nor this callback grants display. */
   if(phase==NES_PLAN215_FINISH && p->bank_history==2 && p->window->last[1]==2 && p->window->wait){
    uint8_t ack[12];
    if(!nes_window184_drain(p->window,ack) ||
       !p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,5);
   }
   if(!nes_sink195_submit(p->sink,d))return fail(p,5);''')
    if multi:
        s=once(s,'if(phase==NES_PLAN215_FINISH && p->bank_history==2 && p->window->last[1]==2 && p->window->wait){',
            'if(phase==NES_PLAN215_FINISH && (d[3] || d[2]>(d[1]?32:16)) && p->bank_history==2 && p->window->last[1]==2 && p->window->wait){')
    if credit:
        assert not multi
        s=once(s,'if(phase==NES_PLAN215_FINISH && p->bank_history==2 && p->window->last[1]==2 && p->window->wait){',
            'if(p->ending && p->bank_history==2 && p->window->last[1]==2 && p->window->wait){')
    p.write_text(s,newline='\n')
    if credit:
        p=out/'src/nes_native_runtime165.c'
        s=once(p.read_text(),'''   --s->prefetch_left;
   if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
  }
  return check(ctx);''','''   uint16_t before=r->next_token;
   if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
   /* Empty STATUS must not spend one of the seven geometry blocks. READ,
    * CRC/restore and checked POP all succeeded before this debit. */
   if(r->next_token!=before)--s->prefetch_left;
  }
  return check(ctx);''')
        p.write_text(s,newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--multi',action='store_true')
    p.add_argument('--credit',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.multi,a.credit)
