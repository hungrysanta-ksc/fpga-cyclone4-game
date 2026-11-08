"""Service the initial blank tile before one warm BG pair; retain later large batches."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest,evidence
from nes_raw506 import once


def prepare(base,out):
    assert digest(base/'src/obj-nes-100/firmware.stm')==evidence('trial666-package.json')['firmware_SHA256']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_plan_service200.c'
    s=p.read_text()
    s=once(s,'static bool poll(','''/* One initial compact BG pair only. Bank credit is independent of the
 * still-owned tile descriptor; its receipt and final display ACK stay owed. */
static bool bg675(const struct nes_plan200 *p){
 return p->bank_history==2 && !p->ending && p->sent==1 && p->count==2 &&
        p->bytes==14 && p->buffer[4]==0x80 && p->buffer[11]==0x80;
}
static bool poll(''')
    s=once(s,'''if(phase==NES_PLAN215_FLUSH && rx[3]==1 && p->ending && p->count==1 &&
     p->buffer[4]==0x83)result|=1;''','''if(phase==NES_PLAN215_FLUSH && rx[3]==1 &&
     ((p->ending && p->count==1 && p->buffer[4]==0x83) || bg675(p)))result|=1;''')
    # Keep the original larger BG/OBJ boundary after the extra initial pair.
    assert s.count('p->bank_history==2 && p->sent==1 &&')==2
    s=s.replace('p->bank_history==2 && p->sent==1 &&','p->bank_history==2 && p->sent<=2 &&')
    s=once(s,'''  if(!p->early)return nes_plan549_first(p);
  /* Confirmed BG records''','''  if(!p->early)return nes_plan549_first(p);
  /* Start zero-tile consumption while the next BG is being prepared. Do not
   * add a transaction to a frame containing only its first BG record. */
  if(p->bank_history==2 && p->sent==1 && p->count==1 && !p->bulk_valid){
   uint8_t flags;if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;
  }
  if(bg675(p))return flush(p);
  /* Confirmed BG records''')
    p.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.base,a.out)
