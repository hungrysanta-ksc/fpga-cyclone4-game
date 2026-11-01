# SPDX-License-Identifier: MIT
"""Refresh a stale three-credit snapshot once per idle E8 so the next settled map can use returned credit."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once,sha

def prepare(src,out):
    root=Path(__file__).resolve().parents[1]
    assert sha(src/'obj-nes-100/firmware.stm')==json.loads((root/'analysis/flash529-verification.json').read_text())['firmware_SHA256']
    out.mkdir(parents=True,exist_ok=False)
    def edit(name,old,new):
        (out/name).write_text(once((src/name).read_text(),old,new),newline='\n')
    edit('nes_sink_window184.h','bool nes_window184_init(','bool nes_window532_room(struct nes_sink_window184 *,bool *);\nbool nes_window184_init(')
    edit('nes_sink_window184.c','bool nes_window184_init(','''bool nes_window532_room(struct nes_sink_window184 *s,bool *room){
 if((uint16_t)(s->sent-s->retired)>=3){
  uint8_t ack[12];
  if(!status(s,ack))return false;
  if(s->retired==s->sent && (ack[0]!=0 || ack[1]!=s->last[0] ||
     memcmp(ack+2,s->last+2,8) || ack[10]!=0x65 || ack[11]!=0x9a))return fail(s,8);
 }
 *room=(uint16_t)(s->sent-s->retired)<3;
 return true;
}
bool nes_window184_init(''')
    edit('nes_plan_service200.c','''if(flags==0 && p->quiet_map && (uint16_t)(p->window->sent-p->window->retired)<3)
   if(!p->quiet_map(p->ctx))return fail(p,5);''','''if(flags==0 && p->quiet_map){
   bool room;
   if(!nes_window532_room(p->window,&room))return fail(p,5);
   /* Refresh can admit more than four subsequent map packets. Resolve the
    * outstanding bulk through its checked window while its target is live. */
   if(room && p->bulk_pending && (uint16_t)(p->window->sent-p->bulk_until)>=3 &&
      !complete485(p))return false;
   if(room && !p->quiet_map(p->ctx))return fail(p,5);
  }''')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.arm,a.out)
