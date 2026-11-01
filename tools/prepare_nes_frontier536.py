# SPDX-License-Identifier: MIT
"""Offer at most one further canonical map packet once its BG rows are immutable."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once,sha

def prepare(src,out,compact_raw=False):
    root=Path(__file__).resolve().parents[1]
    assert sha(src/'obj-nes-100/firmware.stm')==json.loads((root/'analysis/trial533-verification.json').read_text())['firmware_SHA256']
    out.mkdir(parents=True,exist_ok=False)
    name='nes_planner211.c'
    s=once((src/name).read_text(),'bool offered=false;','unsigned offered=0,next_group=3;')
    s=once(s,'resident->offer_map && !offered && g>=3','resident->offer_map && offered<2 && g>=next_group')
    s=once(s,'offered=true;if(!resident->offer_map','offered++;next_group=g+3;if(!resident->offer_map')
    s=once(s,'if(!offered && resident->offer_map','if(offered<2 && resident->offer_map')
    (out/name).write_text(s,newline='\n')

    if compact_raw:
        # For the short, already packed CHR only, issue ordinary mixed-data
        # packets instead of splitting out identical-word subranges. The
        # general wire encoder may still compress a wholly uniform packet.
        name='nes_native_sink165.c'
        s=once((src/name).read_text(),'   if(!span(s,5,offset,parts[part],lengths[part]))return false;',
               '''   if(part==0 && packed<=384){
    for(unsigned at=0;at<packed;at+=240){
     unsigned n=packed-at;if(n>240)n=240;
     if(!packet(s,2,5,offset+at,raw+at,n))return false;
    }
   }else if(!span(s,5,offset,parts[part],lengths[part]))return false;''')
        (out/name).write_text(s,newline='\n')
    name='nes_native_runtime165.c'
    s=once((src/name).read_text(),' return nes_sink527_early(&s->sink,s->video,s->resident);',''' if(!s->sink.map_next)return nes_sink527_early(&s->sink,s->video,s->resident);
 /* A failed first offer keeps its one-shot sentinel. On the second frontier
  * the preceding packet ended no later than the current finalized prefix. */
 if(s->sink.map_next>=64)return true;
 bool room;
 if(!nes_window532_room(&s->transport,&room))return false;
 if(!room || (s->plan.bulk_pending && (uint16_t)(s->transport.sent-s->plan.bulk_until)>=3))return true;
 if(!nes_plan527_map_credit(&s->plan,&room))return false;
 return !room || map527(&s->sink,s->video,s->resident->map_stale[s->resident->target]|s->video->map_dirty,true);''')
    (out/name).write_text(s,newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--compact-raw',action='store_true')
    a=p.parse_args();prepare(a.arm,a.out,a.compact_raw)
