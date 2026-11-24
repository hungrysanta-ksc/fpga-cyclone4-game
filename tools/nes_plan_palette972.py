"""Issue the last full E9 before palette construction on the MMC966 ARM."""
import argparse
import shutil
from pathlib import Path

from nes_page963 import simulate
from nes_raw506 import once
from package_nes_trial966 import WORK as BASE


def prepare(work, prefix):
    shutil.copytree(BASE / "link", work / "link")
    path = work / "link/src/nes_native_runtime165.c"
    # END is the fifteenth record. append() can flush during the append;
    # nes_plan200_end still owns the returned count and final ending flag.
    path.write_text(once(path.read_text(), "p->count>=14 || p->bytes>208",
                         "p->count>14 || p->bytes>208"), newline="\n")
    if not prefix:
        return
    src = path.parent
    header = src / "nes_native_video165.h"
    header.write_text(once(header.read_text(),"bool scroll_issued;",
                           "bool scroll_issued, prefix_due972, prefix_sent972;"),newline="\n")
    runtime = once(path.read_text()," return p->sent || !p->count",
                   """ s->video->prefix_due972=!p->sent && p->count==14 && p->bytes<=208 &&
   s->video->patch_count==1 && !(s->video->map_dirty | s->resident->map_stale[s->resident->target]);
 return p->sent || !p->count""")
    header = src/"nes_native_sink165.h"
    header.write_text(once(header.read_text(),"bool nes_scroll810(",
                           "bool nes_prefix972(struct nes_native_sink165 *,struct nes_native_video165 *);\nbool nes_scroll810("),newline="\n")
    path.write_text(once(runtime,"static bool offer527(", """bool nes_plan_prefix972(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 return s->plan.ending && !s->plan.count && nes_prefix972(&s->sink,s->video);
}
static bool offer527("""),newline="\n")
    planner = src/"nes_planner211.c"
    text = planner.read_text()
    marker = text.index(" if(p->patch_count){",text.index(" /* CGRAM becomes"))
    planner.write_text(text[:marker]+""" if(p->prefix_due972){
  extern bool nes_plan_prefix972(void *);
  if(!nes_plan_prefix972(resident->ctx))return fail(p,7);
 }
"""+text[marker:],newline="\n")
    sink = src/"nes_native_sink165.c"
    text = once(sink.read_text(),"bool nes_scroll810(", """bool nes_prefix972(struct nes_native_sink165 *s,struct nes_native_video165 *p){
 /* No map queued here. Preserve ordinary queue credit, standard literal
  * framing and the final bank identity/coverage checks. */
 if(!packet(s,24,3,0,p->cgram,32))return false;
 p->prefix_sent972=true;
 return true;
}
bool nes_scroll810(""")
    text = once(text,"bool reuse=same&&","bool reuse=!p->prefix_sent972&&same&&")
    sink.write_text(once(text," if(!span(s,3,0,p->cgram,512))return false;",""" if(p->prefix_sent972){
  if(!packet(s,2,3,32,p->cgram+32,96) ||
     !packet(s,2,3,128,p->cgram+128,232) ||
     !packet(s,2,3,360,p->cgram+360,152))return false;
 }else if(!span(s,3,0,p->cgram,512))return false;"""),newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare","run"))
    parser.add_argument("temp", type=Path)
    parser.add_argument("--phase", type=int, choices=(1,2), default=1)
    parser.add_argument("--prefix", action="store_true")
    args = parser.parse_args()
    work = BASE.with_name("nes-plan-palette972" + ("-prefix" if args.prefix else ""))
    if args.action == "prepare":
        prepare(work,args.prefix)
    else:
        simulate(args.temp,args.phase,"cold",True,work,True,
                 tag="972prefix" if args.prefix else "972end",edition=966)
