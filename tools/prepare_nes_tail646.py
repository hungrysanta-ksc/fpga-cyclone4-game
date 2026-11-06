"""Two disjoint ARM candidates on the pinned MMC643 image; no new wire opcodes."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest, evidence
from nes_raw506 import once


def prepare(base, out, mode):
    assert digest(base/"src/obj-nes-100/firmware.stm")==evidence("reject643-package.json")["firmware_SHA256"]
    shutil.copytree(base,out,ignore=shutil.ignore_patterns("obj-*",".dep-*","*.log"))
    src=out/"src"
    sink=src/"nes_native_sink165.c"
    code=sink.read_text()
    if mode=="grant":
        header=src/"nes_native_sink165.h"
        header.write_text(once(header.read_text(),"bool displayed;uint8_t map_next;",
                               "bool displayed,early_oam646;uint8_t map_next;"),newline="\n")
        code=once(code,"s->map_next=0;s->sequence=0;","s->map_next=0;s->early_oam646=false;s->sequence=0;")
        code=once(code,"op!=23 && op!=24 &&","op!=23 && op!=24 && op!=25 &&")
        code=once(code,"if(op==24)op=2;","if(op==25)op=9; /* Already arbitrated END wait. */\n if(op==24)op=2;")
        code=once(code,"return packet_wire(s,9,4,0,cmd,sizeof cmd,0);",
                  "return packet_wire(s,s->plan && s->plan->quiet_map?25:9,4,0,cmd,sizeof cmd,0);")
        pos=code.index("static void",code.index("return packet_wire(s,s->plan"))
        code=code[:pos]+"""/* Called only in the existing credit-checked quiet-map callback. */
bool nes_offer646(struct nes_native_sink165 *s,const struct nes_native_video165 *p){
 if(!s->early_oam646 && !s->plan->bulk_pending && p->valid && s->displayed &&
    s->generation==p->generation && s->ack635[0] && s->ack635[1] && same635(s,p)){
  if(!send635(s,p,(s->serial-1)&1u))return false;
  s->early_oam646=true;
 }
 return true;
}
"""+code[pos:]
        code=once(code,"if(!send635(s,p,r->target))","if(!s->early_oam646 && !send635(s,p,r->target))")
        runtime=src/"nes_native_runtime165.c"
        text=once(runtime.read_text(),"static bool quiet528(void *ctx){",
                  "bool nes_offer646(struct nes_native_sink165 *,const struct nes_native_video165 *);\nstatic bool quiet528(void *ctx){")
        text=once(text," unsigned before=s->sink.map_next;"," if(!s->sink.early_oam646){\n  if(!nes_offer646(&s->sink,s->video))return false;\n  if(s->sink.early_oam646)return true; /* One non-preemptive transaction per grant. */\n }\n unsigned before=s->sink.map_next;")
        runtime.write_text(text,newline="\n")
    elif mode=="short":
        # The final enable table is 81 B. Preserve every source byte, even
        # if the padding becomes nonzero: packet() only compresses equal words.
        code=once(code,"if(!span(s,5,offset,tables,243))return false;",
                  """unsigned pad=81-p->patch.size[2];
  if(pad>=4 && !(pad&1)){
   if(!span(s,5,offset,tables,243-pad) ||
      !packet(s,2,5,offset+243-pad,tables+243-pad,pad))return false;
  }else if(!span(s,5,offset,tables,243))return false;""")
    else:
        raise ValueError(mode)
    sink.write_text(code,newline="\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("base",type=Path)
    parser.add_argument("out",type=Path)
    parser.add_argument("mode",choices=("grant","short"))
    a=parser.parse_args()
    prepare(a.base,a.out,a.mode)
