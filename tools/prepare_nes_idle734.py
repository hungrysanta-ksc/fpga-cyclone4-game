"""733 Flash saving; protect a split-map tail using the existing719 deadline.

After ordinary was issued between extents, one advisory DMA event cannot
release the remaining-map opportunity. Keep the same finite ACK-based budget,
checked drain, STOP, input callback and expiry; no new timing constant or ABI.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in ('175733117baa8f0b424070b8dc97084b397b3dfe4ba77846970630ae3532dc54','37d4dd149e8ccd10656bf0cea7b984cc1a1a03574ce7e25941083be812176dd0')
 a.out.mkdir(parents=True,exist_ok=False)
 p=a.out/'nes_native_sink165.c';s=(a.base/p.name).read_text()
 s=once(s,'if((w->status_flags&8) || !w->wait)break;',
 '''/*734 Ordinary split these accepted extents. A single DMA event
     * is not tail completion; keep the existing bounded opportunity.
     * Expiry still releases output, and every iteration checks STOP. */
    if((!pass && (w->status_flags&8)) || !w->wait)break;''')
 if a.short_tail:
  s=once(s,'for(unsigned pass=0;;pass++){', '''for(unsigned pass=0;;pass++){
  /*734B Only a remaining span no wider than one384B map pair owns the
   * extra idle opportunity. Large extents retain the original progress
   * release so the next frame's BG producer keeps its ROM window. */
  if(pass && s->map_next<64){
   uint64_t tail=r->map_upload>>s->map_next;
   while(tail && !(tail&1))tail>>=1;
   if(tail && tail<=63)pass=2;
  }''')
  s=once(s,'if((!pass && (w->status_flags&8)) || !w->wait)break;',
              'if((pass!=2 && (w->status_flags&8)) || !w->wait)break;')
 p.write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe734.json')).write_text(json.dumps(dict(stage=734,short_tail=a.short_tail,scope=__doc__,base=sha(a.base/'obj-nes-100/firmware.stm'),source=sha(p),new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n',encoding='utf8',newline='\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--short-tail',action='store_true')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
