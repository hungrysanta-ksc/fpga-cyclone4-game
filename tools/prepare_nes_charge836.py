"""Recognize the five repeated rows directly in the planner's CHR layout."""
import argparse

from nes_charge836 import OUT, PROBES
from nes_raw506 import once
from link_nes_section832 import build

BASE=PROBES/"nes-output823/link-835progress"


def sender(mode):
    text=(BASE/"src/nes_native_sink165.c").read_text()
    start=text.index("static bool raw833(")
    end=text.index("bool nes_sink212_seal(",start)
    text=text[:start]+"""static bool words836(const uint8_t *chr,uint8_t words[10]){
 /* Compare all 32 tiles. The first plane pair must also agree across
  * both fine rows. Read only initialized bytes of the NES CHR image. */
 for(unsigned plane=0;plane<3;plane++){
  const uint8_t *src=chr+16*plane;
  uint32_t first;
  memcpy(&first,src,4);
  if(!plane && (uint16_t)first!=(first>>16))return false;
  for(unsigned t=1;t<32;t++){
   uint32_t v;
   memcpy(&v,src+64*t,4);
   if(v!=first)return false;
  }
  if(!plane)memcpy(words,src,2);
  else memcpy(words+4*plane-2,src,4);
 }
 return true;
}
"""+text[end:]
    text=once(text,"  if(p->patch_count && p->patch_count<=2){","""  uint8_t words[10];
  bool repeated=p->patch_count==2 && words836(raw,words);
  if(repeated)packed=384;
  else if(p->patch_count && p->patch_count<=2){""")
    text=once(text,"if(!raw833(s,raw,packed))return false;",
              "if(repeated){if(!packet(s,9,5,1121,words,sizeof words))return false;}\n  else if(!span(s,5,1121,raw,packed))return false;")
    if mode in ("early","split"):
        text=once(text," bool same=same635(s,p);",""" bool issued=repeated && p->scroll_issued && p->map_dirty;
 if(issued && !packet(s,9,5,1121,words,sizeof words))return false;
 bool same=same635(s,p);""")
        text=once(text,"if(repeated){if(!packet","if(repeated){if(!issued && !packet")
    if mode=="split":
        # The fourth head can now retire well before blank. Observe its
        # independently checked DMA progress before occupying the same SPI
        # window with the next map. Keep the original bounded fallback.
        text=once(text,"for(unsigned n=0;n<12;n++)","for(unsigned n=0;n<120;n++)")
    dst=OUT/("patch-"+mode)
    dst.mkdir(exist_ok=True,parents=True)
    (dst/"nes_native_sink165.c").write_text(text,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("direct","early","split"))
    p.add_argument("--overlay",action="store_true")
    a=p.parse_args()
    if a.overlay:
        build(a.mode,PROBES/("nes-output823/link-836"+a.mode),OUT,"nes_scroll810")
    else:
        sender(a.mode)
