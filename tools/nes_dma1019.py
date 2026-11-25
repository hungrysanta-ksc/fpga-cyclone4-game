"""Bounded MMC1012 ARM comparison using the existing checked E0 map-completion bit."""
import argparse
import json
import shutil
from pathlib import Path

from nes_overlap1018 import BASE, ROOT, once, sha
from replay_nes_tail1013 import run

WORK = BASE.with_name("nes-dma1019") / "e0"


def prepare():
    src = BASE / "link"
    ref = json.loads((ROOT/"analysis/trial1012-package.json").read_bytes())
    assert sha(src/"src/obj-nes-100/firmware.stm")==ref["firmware"]
    dest = WORK / "link"
    shutil.copytree(src,dest,ignore=shutil.ignore_patterns("*.log"))
    path=dest/"src/nes_native_sink165.c"
    text=once(path.read_text(), " if(!map527(s,p,r->map_upload,false))return false;", """
 bool trigger = r->map_upload==0x7fffff && (s->map_next&127)==12 &&
                p->patch_count==1 && p->scroll_issued && s->displayed &&
                s->ack635[r->target] && s->ack635[1-r->target] && same635(s,p);
 if(!map527(s,p,r->map_upload,trigger?1:0))return false;
 if(trigger){
  struct nes_sink_window184 *w=s->plan->window;
  if(!wait_map880(w,12))return fail(s,5);
  /* The checked flag is scoped to the retired head. On timeout restore the
   * usual drain before offering any section-5 packet. */
  if(!(w->status_flags&8)){
   if(!map527(s,p,r->map_upload,false))return false;
   trigger=false;
  }
 }""")
    text=once(text,"  offset+=192;", "  if(trigger && !map527(s,p,r->map_upload,false))return false;\n  offset+=192;")
    path.write_text(text,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--temp",type=Path)
    action=p.add_mutually_exclusive_group()
    action.add_argument("--phase",type=int,choices=(1,2))
    action.add_argument("--guards",action="store_true")
    a=p.parse_args()
    if a.phase or a.guards:
        if not a.temp:
            p.error("replay and guards require --temp")
        if a.guards:
            from guard_nes_tail1013 import guards
            guards(a.temp,"e0",root=WORK,trace=a.temp/"nes-tile821-late-jointmirror-p1-1019-e0",
                   tag="nes-dma1019-e0-guard")
        else:
            run(a.temp,a.phase,"control",firmware=WORK/"link/src",tag="1019-e0")
    else:
        prepare()
