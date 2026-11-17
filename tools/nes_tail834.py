"""Issue the scroll/padding prefix while palette or OAM work is pending."""
import argparse

from nes_raw506 import once
from nes_repeat833 import PROBES
from link_nes_section832 import build

OUT=PROBES/"nes-tail834"
BASE=PROBES/"nes-output823/link-833stock"
MODES=("palette","oam","bg","bgidle","bgpre","bgdirty")


def prepare(mode):
    text=(BASE/"src/nes_native_sink165.c").read_text()
    dest=OUT/("patch-"+mode)
    dest.mkdir(exist_ok=True,parents=True)
    if mode.startswith("bg"):
        # The long right-page map has already been queued. Bulk may have
        # appeared during that drain; both ordinary sends recheck it.
        text=once(text,"  if(fragments>112/4){","""  if(fragments>112/4 && p->patch_count==2 && !(uint32_t)map && !p->scroll_issued){
   if(!(n&1))p->hdma[n++]=0;
   if(!packet(s,2,5,0,p->hdma,n) || !packet_wire(s,5,5,n,zero,2,1121-n))return false;
   p->scroll_issued=true;
   return true;
  }
  if(fragments>112/4){""")
        if mode in ("bgidle","bgpre","bgdirty"):
            # A started producer may hold a first record only in ARM RAM.
            # No accepted plan and no outstanding bulk receipt can be displaced.
            allowance=("!s->plan->started" if mode=="bgidle" else
                       "s->plan->started && !s->plan->ending && !s->plan->sent")
            if mode=="bgdirty":
                allowance+=" && p->map_dirty"
            text=once(text,"&& !(uint32_t)map && !p->scroll_issued){",
                      "&& !(uint32_t)map && !p->scroll_issued && "+allowance+" && !s->plan->bulk_pending){")
            text=once(text,"if(!packet(s,2,5,0,p->hdma,n) || !packet_wire(s,5,5,n,zero,2,1121-n))",
                      "if(!packet(s,24,5,0,p->hdma,n) || !packet_wire(s,25,5,n,zero,2,1121-n))")
        (dest/"nes_native_sink165.c").write_text(text,newline="\n")
        return
    start=text.index(" if(!p->scroll_issued && !span(s,5")
    end=text.index("  /* Read the enclosing object",start)
    prefix=text[start:end]
    text=text[:start]+""" if(!prefix_sent && !prefix834(s,p))return false;
 if(p->patch_count){
  unsigned offset=1121;
"""+text[end:]
    declaration="static bool prefix834(struct nes_native_sink165 *s,const struct nes_native_video165 *p){\n"
    text=once(text,"bool nes_sink212_seal(",declaration+prefix+" }\n return true;\n}\nbool nes_sink212_seal(")
    text=once(text," bool same=same635(s,p);"," bool prefix_sent=false;\n bool same=same635(s,p);")
    original=" if(!span(s,3,0,p->cgram,512))return false;"
    eligible="packed==384 && p->objects>28 && p->map_dirty && !(uint32_t)r->map_upload && s->plan && s->plan->bank_history==2"
    if mode=="palette":
        changed=f""" if({eligible}){{
  if(!span(s,3,0,p->cgram,128) || !prefix834(s,p) ||
     !span(s,3,128,p->cgram+128,384))return false;
  prefix_sent=true;
 }}else"""+original
    elif mode=="oam":
        changed=original+f"""
 if({eligible}){{
  if(!prefix834(s,p))return false;
  prefix_sent=true;
 }}"""
    else:
        raise ValueError(mode)
    text=once(text,original,changed)
    (dest/"nes_native_sink165.c").write_text(text,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=MODES)
    p.add_argument("--overlay",action="store_true")
    a=p.parse_args()
    if a.overlay:
        build(a.mode,PROBES/("nes-output823/link-834"+a.mode),OUT,"nes_scroll810" if a.mode.startswith("bg") else None)
    else:
        prepare(a.mode)
