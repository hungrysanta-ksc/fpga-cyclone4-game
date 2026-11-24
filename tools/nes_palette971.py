"""Build and compare an early committed-input palette on the MMC966 ARM and 65816."""
import argparse
import shutil
from pathlib import Path

from nes_raw506 import once
from package_nes_trial966 import WORK as BASE
from nes_page963 import simulate

WORK = BASE.with_name("nes-palette971")
DIRECT = BASE.with_name("nes-palette971-direct")
PAIR = BASE.with_name("nes-palette971-pair")


def prepare(work):
    shutil.copytree(BASE / "link", work / "link")
    src = work / "link/src"
    header = src / "nes_native_video165.h"
    header.write_text(once(header.read_text(), "bool scroll_issued;", "bool scroll_issued, palette_issued;"), newline="\n")
    planner = src / "nes_planner211.c"
    body = planner.read_text()
    start = body.index(" /* CGRAM becomes")
    stop = body.index(" if(p->patch_count){",start)
    palette = body[body.index(" memset(p->cgram",start):stop]
    patch_colors = "  for(unsigned c=0;c<64;c++)put16(p->cgram+(64+c)*2,lut[c]);"
    body = once(body,body[start:stop],"")
    body = once(body,patch_colors,"")
    # All input palette bounds and the raw count have been checked. OBJ slot
    # allocation uses OAM and expired BG keys; neither is a palette input.
    body = once(body," unsigned at=0;\n for(unsigned y=0;y<224;){",
                palette+" if(p->patch_count){\n"+patch_colors+"\n }\n unsigned at=0;\n for(unsigned y=0;y<224;){")
    if work == PAIR:
        begin = body.index(" if(p->patch_count){\n  /* No BG allocation")
        end = body.index(" p->valid=true",begin)
        raw = body[begin:end]
        body = once(body,raw,"")
        body = once(body," unsigned at=0;\n for(unsigned y=0;y<224;){",raw+" unsigned at=0;\n for(unsigned y=0;y<224;){")
        # Only the first 2,298 bytes of the expired 8KiB BG key table hold
        # the canonical patch. Keep the OBJ checks in disjoint scratch.
        body = once(body,"*rank_used=(uint8_t *)p->bg_keys,","*rank_used=(uint8_t *)p->bg_keys+3072,")
    planner.write_text(body,newline="\n")
    sink = src / "nes_native_sink165.c"
    body = once(sink.read_text(), " p->scroll_issued=true;", """ p->scroll_issued=true;
 if(!map && p->patch_count==1 && !p->palette_issued){
  if(!span(s,3,0,p->cgram,sizeof(p->cgram)))return false;
  p->palette_issued=true;
 }""")
    body = once(body,"bool reuse=same&&","bool reuse=!p->palette_issued&&same&&")
    body = once(body,"if(!span(s,3,0,p->cgram,512))","if(!p->palette_issued && !span(s,3,0,p->cgram,512))")
    if work in (DIRECT,PAIR):
        body = once(body,"  if(!span(s,3,0,p->cgram,sizeof(p->cgram)))return false;", """  /* A pre-END head still passes through normal queue credit and live STOP
   * checks. Use the same internal literal selector as the scroll above. */
  static const uint8_t sizes[]={32,96,232,152};
  unsigned at=0;
  for(unsigned i=0;i<sizeof sizes;i++){
   if(!packet(s,24,3,at,p->cgram+at,sizes[i]))return false;
   at+=sizes[i];
  }""")
    if work == PAIR:
        pack_start = body.index("  /* Canonical raw CHR")
        pack_end = body.index(" bool same=same635",pack_start)
        pack = body[pack_start:pack_end]
        tail_start = body.index("  /* Read the enclosing object")
        tail_end = body.index("  put16(descriptor+10,offset+249);")
        tail = body[tail_start:tail_end]
        body = once(body,pack,"")
        body = once(body,tail+"  put16(descriptor+10,offset+249);", """  unsigned end=1562;
  if(!p->palette_issued && !patch971(s,p,offset,2,&end))return false;
  put16(descriptor+10,end);""")
        helper = "static bool patch971(struct nes_native_sink165 *s,struct nes_native_video165 *p,unsigned offset,unsigned op,unsigned *end){\n"+pack+tail+"  *end=offset+249;return true;\n}\n"
        helper = helper.replace("packet(s,2,5,offset,joined","packet(s,op,5,offset,joined").replace("packet(s,2,5,offset+201,joined","packet(s,op,5,offset+201,joined")
        body = once(body,"bool nes_scroll810(",helper+"bool nes_scroll810(")
        body = once(body,"  p->palette_issued=true;","  unsigned end;\n  if(!patch971(s,p,1121,24,&end) || end!=1562)return false;\n  p->palette_issued=true;")
    sink.write_text(body,newline="\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("prepare","prepare-direct","prepare-pair","control","early","direct","pair"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--tag")
    args=p.parse_args()
    if args.mode.startswith("prepare"):
        prepare({"prepare":WORK,"prepare-direct":DIRECT,"prepare-pair":PAIR}[args.mode])
    else:
        simulate(args.temp,args.phase,"cold",True,{"control":BASE,"early":WORK,"direct":DIRECT,"pair":PAIR}[args.mode],
                 True,tag=args.tag or "971"+args.mode,edition=966)
