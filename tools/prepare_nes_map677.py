"""Reserve a bulk slot while publishing bounded maps behind an already owned tile."""
import argparse,shutil
from pathlib import Path
from check_nes_fault641 import digest,evidence
from nes_raw506 import once

def prepare(base,out,mode='reserve'):
    assert digest(base/'src/obj-nes-100/firmware.stm')==evidence('idle676-verification.json')['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_plan_service200.c'
    guard=''' /* Finish the already owned bulk before continuing a warm map run.
  * Its checked receipt is distinct from a new producer query. Subsequent
  * map heads use the ordinary four-credit queue; FINAL/ordinary service
  * the held next tile after the map run, without dropping its identity. */
 if(mode==NES_MAP553 && p->bank_history==2 && p->window && p->window->last[1]==2){
  if(!valid(p))return false;
  return complete485(p);
 }
''' if mode=='run' else ''' /* The existing bulk owns its token until checked completion. Publish a
  * bounded map suffix behind it without re-querying the same producer.
  * Keep one queue slot reserved, and never age the bulk past through()'s
  * four-packet completion window. FINAL/ordinary still service the producer. */
 if(mode==NES_MAP553 && p->bulk_pending && p->window &&
    (uint16_t)(p->window->sent-p->bulk_until)<3 &&
    (uint16_t)(p->window->sent-p->window->retired)<3)return valid(p);
'''
    old=''' uint8_t flags;
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!poll(p,&flags,NES_PLAN215_FINISH))return false;'''
    s=once(p.read_text(),old,guard+old)
    p.write_text(s,newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--mode',choices=('reserve','run'),default='reserve')
    a=p.parse_args();prepare(a.base,a.out,a.mode)
