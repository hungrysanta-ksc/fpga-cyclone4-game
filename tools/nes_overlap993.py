"""Overlap checked 201/240-byte section-5 submissions with the accepted OBJ/OAM stream."""
import argparse
import shutil
from pathlib import Path

import nes_page963
from nes_hdma990 import BASE
from nes_raw506 import once

ROOT=BASE.parent/"nes-overlap993"
MODES=("prep","split","both")


def prepare(mode):
    root=ROOT/mode/"link"
    shutil.copytree(BASE/"link",root)
    path=root/"src/nes_native_sink165.c"
    s=path.read_text()
    start=s.index("  /* Read the enclosing object representation")
    end=s.index("  if(!packet(s,2,5,offset,joined,201))",start)
    old=s[start:end]
    table=old[old.index("  _Static_assert"):old.index("  /* One contiguous")]
    copy=old[old.index("  memcpy(joined,raw+prefix,192);"):]
    remainder=old.replace(table,"").replace(copy,"")
    s=once(s,old,remainder)
    helper="static void join993(struct nes_native_video165 *p,uint8_t *joined,const uint8_t *raw){\n"+table+copy.replace("raw+prefix","raw")+"}\n"
    s=once(s,"bool nes_sink212_seal(",helper+"bool nes_sink212_seal(")
    s=once(s," bool same=same635(s,p);"," bool earlier=p->prefix_sent972 && p->scroll_issued && packed==192;\n bool same=same635(s,p);")
    # The final palette submissions keep the original bulk progress calls.
    # At this point both OBJ descriptors have had their ordinary scheduling opportunity.
    insert=" if(earlier){\n  uint8_t *joined=(uint8_t *)p->bg_keys+6144;\n  join993(p,joined,raw);\n"
    if mode in ("split","both"):
        insert+="  if(!packet(s,2,5,1121,joined,201))return false;\n"
    if mode=="both":
        insert+="  if(!packet(s,2,5,1322,joined+201,240))return false;\n"
    s=once(s," if(!oam227(s,p->oam))",insert+" }\n if(!oam227(s,p->oam))")
    s=once(s,"  if(!packet(s,2,5,offset,joined,201))","  if(!earlier)join993(p,joined,raw+prefix);\n  if("+("!earlier && " if mode!="prep" else "")+"!packet(s,2,5,offset,joined,201))")
    if mode=="both":
        s=once(s,"  if(!packet(s,2,5,offset+201","  if(!earlier && !packet(s,2,5,offset+201")
        # Internally mark only this finished section-5 schedule. Wire SEAL, final
        # plan gate, credit, queue identity checks and post-send drain still run.
        w=root/"src/nes_sink_window184.c"
        old=w.read_text()
        h=root/"src/nes_sink_window184.h"
        h.write_text(once(h.read_text(),"uint8_t status_flags,ack_status;","uint8_t status_flags,ack_status;\n bool joined_tail993;"),newline="\n")
        s=once(s," if(!packet(s,3,0,0,descriptor"," if(s->plan && s->plan->window)s->plan->window->joined_tail993=earlier;\n if(!packet(s,3,0,0,descriptor")
        marker="p[0]!=3 || s->last[1]!=5"
        w.write_text(once(old,marker,"p[0]!=3 || (s->last[1]!=5 && !(s->joined_tail993 && s->last[1]==4 && s->last[0]==4 && s->last[8]==p[8] && s->last[9]==p[9]))"),newline="\n")
    path.write_text(s,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run"));p.add_argument("mode",choices=MODES)
    p.add_argument("temp",type=Path,nargs="?");p.add_argument("phase",type=int,nargs="?",choices=(1,2))
    a=p.parse_args()
    if a.action=="prepare":prepare(a.mode)
    else:nes_page963.simulate(a.temp,a.phase,"cold",True,ROOT/a.mode,True,tag="993"+a.mode,edition=966)
