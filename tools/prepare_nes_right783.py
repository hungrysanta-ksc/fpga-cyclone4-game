# SPDX-License-Identifier: MIT
"""Send one complete four-row island from the right page while BG planning continues."""
import argparse
from pathlib import Path
from nes_raw506 import once,sha


def prepare(base,out):
    assert sha(base/"obj-nes-100/sd2snes.elf")=="7193456ca235672c4f116bd30581a1a3b81fadf7f822e95ad9b092ad52ff0a87"
    out.mkdir(parents=True,exist_ok=False)
    def change(name,*patches):
        s=(base/name).read_text()
        for old,new in patches:
            s=once(s,old,new)
        (out/name).write_text(s,newline="\n")
    change("nes_native_sink165.h",("bool map_pair683;","bool map_pair683;uint8_t right_done;"))
    change("nes_resident211.h",("(*offer_map)(void *,bool)","(*offer_map)(void *,unsigned)"))
    change("nes_native_runtime165.c",("offer527(void *ctx,bool final)","offer527(void *ctx,unsigned final)"),
           (" return nes_sink527_early(", """ if(final>1){
  struct nes_native_video165 *v=s->video;
  struct nes_native_sink165 *sink=&s->sink;
  uint32_t bits=(uint32_t)((v->map_dirty|s->resident->map_stale[s->resident->target])>>32);
  if(sink->right_done || sink->map_next!=128)return true;
  unsigned row=final-5;
  /* final is the number of completed logical rows. The fifth row is the
   * verified hole, so neither packet can grow or change before display. */
  if(!row || (bits>>row&31)!=15 ||
     (bits>>(row-1)&1))return true;


  /* Begin with two free queue positions. Both packets still run the
   * normal checked enqueue. Neither advances the pending bulk receipt. */
  if((uint16_t)(s->transport.sent-s->transport.retired)>2)return true;
  sink->map_next=(uint8_t)(32+row);
  uint64_t run=(uint64_t)bits<<32;
  if(!map527(sink,v,run,1)||!map527(sink,v,run,1))return false;
  sink->right_done=(uint8_t)(32+row);sink->map_next=128;sink->map_pair683=false;
  return true;
 }
 return nes_sink527_early("""))
    change("nes_planner211.c",("row549_done:\n","""row549_done:
 if(early_obj && g>=4 && !resident->offer_map(resident->ctx,g+1))return fail(p,7);
"""))
    change("nes_native_sink165.c",("s->map_next=0;s->map_pair683=false;","s->map_next=s->right_done=0;s->map_pair683=false;"),
           ("  if(!((mask>>g)&1)){", """  if(s->right_done && g==s->right_done){g+=4;pair=false;short_right_tail=true;continue;}
  if(!((mask>>g)&1)){"""))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("base","out"):p.add_argument(n,type=Path)
    a=p.parse_args();prepare(a.base,a.out)
