"""Interleave the literal HDMA tail with the checked OAM repeat and high table."""
import argparse
import shutil
from pathlib import Path

from check_nes_plan975 import directory, packet_path, replay
from nes_cell977 import simulate
from nes_head980 import baseline
from nes_raw506 import once


def work(mode):
    return baseline("returned").with_name("nes-tail986-"+mode)


def prepare(mode):
    dest=work(mode)/"link"
    shutil.copytree(baseline("returned")/"link",dest)
    path=dest/"src/nes_native_sink165.c"
    s=path.read_text()
    s=once(s,"static bool oam227(struct nes_native_sink165 *s,const uint8_t *b){",
           "static bool oam227(struct nes_native_sink165 *s,const uint8_t *b,uint16_t *deferred){")
    begin=" return packet_wire(s,8,4,first,b+first,4,length)&&packet(s,2,4,512,b+512,32);"
    s=once(s,begin,""" if(deferred){
  *deferred=(uint16_t)first;
  RETURN_REPEAT
 }
""".replace("RETURN_REPEAT", "return true;" if mode=="split" else "return packet_wire(s,8,4,first,b+first,4,length);")+begin)
    s=once(s," bool same=same635(s,p);"," uint16_t deferred=UINT16_MAX;\n bool same=same635(s,p);")
    s=once(s," if(!oam227(s,p->oam))return false;",
           " if(!oam227(s,p->oam,p->scroll_issued && p->patch_count==1 && !r->map_upload ? &deferred : NULL))return false;")
    first="  if(!packet(s,2,5,offset,joined,201))return false;"
    if mode=="split":
        s=once(s,first,first+"""
  if(deferred!=UINT16_MAX && !packet_wire(s,8,4,deferred,p->oam+deferred,4,512-deferred))return false;""")
    last="  if(!packet(s,2,5,offset+201,joined+201,240))return false;"
    s=once(s,last,last+"""
  if(deferred!=UINT16_MAX && !packet(s,2,4,512,p->oam+512,32))return false;""")
    if mode=="fifo":
        anchor="  if(deferred!=UINT16_MAX && !packet(s,2,4,512,p->oam+512,32))return false;"
        s=once(s,anchor,anchor+"""
  if(deferred!=UINT16_MAX && s->plan && s->plan->window)
   s->plan->window->oam_tail_before_seal=true;""")
        header=dest/"src/nes_sink_window184.h"
        header.write_text(once(header.read_text(),"bool initialized,ever_sent;",
                               "bool initialized,ever_sent,oam_tail_before_seal;"),newline="\n")
        win=dest/"src/nes_sink_window184.c"
        source=once(win.read_text()," s->sent++;"," s->oam_tail_before_seal=false;\n s->sent++;")
        source=once(source,"(p[0]!=3 || s->last[1]!=5)",
                    "(p[0]!=3 || (s->last[1]!=5 && !s->oam_tail_before_seal))")
        win.write_text(source,newline="\n")
    path.write_text(s,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run","guard"))
    p.add_argument("mode",choices=("high","split","fifo"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--fault",choices=("stop_decode","bad_seal"))
    a=p.parse_args()
    tag="986"+a.mode
    if a.action=="prepare":prepare(a.mode)
    elif a.action=="run":simulate(a.temp,a.phase,"cold",True,work(a.mode),True,tag=tag,edition=966)
    else:
        if not a.fault:p.error("guard requires --fault")
        d=directory(a.temp,a.phase,tag,"cold")
        cmds,_=packet_path(d,911)
        replay(a.temp,d,a.temp/f"nes-{tag}-p{a.phase}-{a.fault}","fixed",cmds,911,a.fault)
