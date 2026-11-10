"""Offer one immutable map packet after warm BG completion using existing credit.

Retain723 row BG/initial pair, cold offers and final map/receipt ownership.
The existing checked producer query has priority; no wait/phase/frame constant,
new persistent state, descriptor or consumer ABI is introduced.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in ('fce656f0769de3ce15de167bfb5a54e5d7ef5f23d372e30c7118c9fd94fc8ca9','5c6a2471eecadd72f5747b78105507f1bf2d78dbf407a14c7511541174167f88')
 n='nes_native_runtime165.c';s=(a.base/n).read_text()
 s=once(s,' if(!final && s->plan.bank_history==2 && s->plan.early)return true;',
 ''' /*726 Completed warm BG may lend one checked-empty producer slot to
  * immutable map. Do not change any in-row BG/ROM supply boundary. Cold
  * retains the original adjacent-only completion policy. */
 if(s->plan.bank_history==2){
  if(!final && s->plan.early)return true;
  final=false;
 }''')
 if a.paired:
  s=once(s,'  final=false;','''  /* Preserve the existing adjacent192B continuation in the same callback.
   * The first packet owns the checked-empty grant; the second retains real
   * queue credit and only exists for the exact contiguous three-row pair. */
  if(final && !nes_sink527_early(&s->sink,s->video,s->resident,false))return false;''')
 files={n:s}
 if a.shared_pair:
  assert not a.paired
  s=(a.base/n).read_text()
  s=once(s,' if(!final && s->plan.bank_history==2 && s->plan.early)return true;',
   ''' unsigned mode=final?2:1;
 if(s->plan.bank_history==2){
  if(!final && s->plan.early)return true;
  if(final)mode=3;
 }''')
  files[n]=once(s,' return nes_sink527_early(&s->sink,s->video,s->resident,final);',' return nes_sink527_early(&s->sink,s->video,s->resident,mode);')
  n='nes_native_sink165.c';s=(a.base/n).read_text()
  s=once(s,'(early==1||adjacent)?24:2','((early&1)||adjacent)?24:2')
  s=once(s,'if(early){s->map_next=(uint8_t)g;s->map_pair683=early==1 && count==3;break;}',
   '''if(early){
   s->map_next=(uint8_t)g;s->map_pair683=early==1 && count==3;
   /*726 One checked-empty grant lends exactly the existing contiguous
    * 192B pair. The second packet still checks real queue credit/STOP.
    * A gap or short first/second extent ends the completion offer. */
   if(early!=3)break;
   early=2;pair=count==3;
  }''')
  s=once(s,'struct nes_resident211 *r,bool final){','struct nes_resident211 *r,unsigned mode){')
  s=once(s,' if(!final){',' if(mode!=2){')
  files[n]=once(s,'final?2:1);','mode);')
  n='nes_native_sink165.h';files[n]=once((a.base/n).read_text(),'struct nes_resident211 *,bool);','struct nes_resident211 *,unsigned);')
 a.out.mkdir(parents=True,exist_ok=False)
 for n,s in files.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=726,paired=a.paired,shared_pair=a.shared_pair,base=sha(a.base/'obj-nes-100/firmware.stm'),sources={n:sha(a.out/n) for n in files},scope=__doc__,new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--paired',action='store_true')
 p.add_argument('--shared-pair',action='store_true')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
