"""Send a confirmed section-5 prefix while the checked tile producer is active."""
import argparse

from nes_raw506 import once
from nes_report828 import reports
from prepare_nes_map828 import PROBES

OUT=PROBES/"nes-section832"
BASE=PROBES/"nes-output823/link-826"


def prepare(mode):
    out=OUT/("patch-"+mode)
    out.mkdir(exist_ok=True,parents=True)
    src=BASE/"src"
    reports(src,out)
    name="nes_native_sink165.c"
    s=(src/name).read_text()
    if mode in ("stream","streammid","streamburst","rleburst"):
        begin=s.index("  unsigned offset=p->scroll_issued?",s.index("bool nes_sink212_seal("))
        stop=s.index("  /* Read the enclosing object",begin)
        pre=s[begin:stop].replace("p->scroll_issued?1121:p->hdma_size","p->hdma_size")
        routine="""static bool begin832(struct nes_native_sink165 *s,struct nes_native_video165 *p){
 if(p->scroll_issued)return true;
 if(!span(s,5,0,p->hdma,p->hdma_size))return false;
"""+pre+" return true;\n}\n"
        s=once(s,"bool nes_sink212_seal(",routine+"bool nes_sink212_seal(")
        s=once(s," bool same=same635(s,p);",""" bool stream=false;
 bool same=same635(s,p);""")
        spot=" if(!span(s,3,0,p->cgram,512))return false;"
        work=""" if(packed==384 && p->objects>28 && p->map_dirty && !(uint32_t)r->map_upload &&
    s->plan && s->plan->bank_history==2){
  uint8_t *bundle=(uint8_t *)p->bg_keys+4096;
  memcpy(bundle+384,p->patch.mode,162);
  memcpy(bundle+546,p->patch.enable,81);
  memcpy(bundle+627,p->patch.size,6);
  if(!begin832(s,p))return false;
  PHASE_ONE
  if(!packet(s,2,5,1121,bundle,240))return false;
  PHASE_TWO
  if(!packet(s,2,5,1361,bundle+240,240) ||
     !packet(s,2,5,1601,bundle+480,153))return false;
  stream=true;
 }else"""+spot
        split=mode!="stream"
        work=work.replace("PHASE_ONE","if(!span(s,3,0,p->cgram,128))return false;" if split else "")
        work=work.replace("PHASE_TWO","if(!span(s,3,128,p->cgram+128,384))return false;" if split else spot.strip())
        if mode in ("streamburst","rleburst"):
            rest="if(!span(s,3,128,p->cgram+128,384))return false;"
            work=once(work,rest,"")
            work=once(work,"  stream=true;","  "+rest+"\n  stream=true;")
        if mode=="rleburst":
            work=once(work,"if(!packet(s,2,5,1121,bundle,240))return false;",
                      "if(!span(s,5,1121,bundle,384))return false;")
            work=once(work,"!packet(s,2,5,1361,bundle+240,240) ||\n     !packet(s,2,5,1601,bundle+480,153)",
                      "!packet(s,2,5,1505,bundle+384,240) ||\n     !packet(s,2,5,1745,bundle+624,9)")
        s=once(s,spot,work)
        s=once(s," if(!p->scroll_issued && !span(s,5"," if(stream){size[5]=1121+633;}else{\n if(!p->scroll_issued && !span(s,5")
        s=once(s," uint8_t descriptor[168];"," }\n uint8_t descriptor[168];")
        (out/name).write_text(s,newline="\n")
        return
    start=s.index(" if(!p->scroll_issued && !span(s,5")
    end=s.index("  /* Read the enclosing object",start)
    prefix=s[start:end]
    off="  unsigned offset=p->scroll_issued?1121:p->hdma_size;"
    helper=prefix+" }\n return true;\n}\n"
    s=s[:start]+""" if(!early && !prefix832(s,p))return false;
 if(p->patch_count){
  unsigned offset=1121;
"""+s[end:]
    head="bool nes_sink212_seal("
    assert off in helper
    s=once(s,head,"static bool prefix832(struct nes_native_sink165 *s,struct nes_native_video165 *p){\n"+helper+"\n"+head)
    if mode not in ("plane","two","whole","woven","credit","table","tableplane","tableoam"):
        raise ValueError(mode)
    n={"plane":128,"two":256,"whole":384,"woven":128,"credit":128,
       "table":0,"tableplane":128,"tableoam":0}[mode]
    work=f""" unsigned early=0;
 /* A warm, newly populated right page with two raw rows. The inherited
  * map case keeps its DMA-progress gate. Packet functions own STOP,
  * CRC, slot credit and the independent bulk receipt. */
 if(packed==384 && p->objects>28 && p->map_dirty && !(uint32_t)r->map_upload &&
    s->plan && s->plan->bank_history==2){{
  if(!prefix832(s,p) || !span(s,5,1121,raw,{n}))return false;
  early={n};
 }}
"""
    s=once(s," bool same=same635(s,p);",work+" bool same=same635(s,p);")
    if mode.startswith("table"):
        first=s.index("  const uint8_t *tables=")
        last=s.index("  size[5]=",first)
        payload=s[first:last]
        s=s[:first]+"  if(!sent_tables && !tables832(s,p,offset))return false;\n"+s[last:]
        s=once(s,head,"static bool tables832(struct nes_native_sink165 *s,struct nes_native_video165 *p,unsigned offset){\n"
               +payload+" return true;\n}\n"+head)
        s=once(s," unsigned early=0;"," unsigned early=0;bool sent_tables=false;")
        original=f"  if(!prefix832(s,p) || !span(s,5,1121,raw,{n}))return false;"
        s=once(s,original, ("  if(!prefix832(s,p))return false;\n" if mode!="tableoam" else "")+
               ("  if(!span(s,5,1121,raw,128))return false;\n" if n else "")+
               ("  if(!tables832(s,p,1121+packed))return false;\n" if mode!="tableoam" else "")+
               "  sent_tables=true;")
        if mode=="tableoam":
            s=once(s," if(!oam227(s,p->oam))return false;",
                   " if(sent_tables && !tables832(s,p,1121+packed))return false;\n if(!oam227(s,p->oam))return false;")
            s=once(s,"  if(!send635(s,p,r->target))return false;",
                   "  sent_tables=false;\n  if(!send635(s,p,r->target))return false;")
        else:
            s=once(s," if(!early && !prefix832(s,p))return false;",
                   " if(!sent_tables && !prefix832(s,p))return false;")
    if mode=="woven":
        s=once(s," if(!oam227(s,p->oam))return false;",""" if(early){
  if(!span(s,5,1121+early,raw+early,128))return false;
  early+=128;
 }
 if(!oam227(s,p->oam))return false;""")
    s=once(s,"if(!span(s,5,offset,raw,packed))return false;",
           "if(early<packed && !span(s,5,offset+early,raw+early,packed-early))return false;")
    if mode=="credit":
        # A second head may use the same recently verified four-slot window.
        # No physical ABI change. Packet enqueue still performs its full
        # admission checks and FINAL still completes all producer receipts.
        s=once(s,"if(!packet_wire(s,5,5,offset,zero,2,n))", """if(!packet_wire(s,s->plan && s->plan->window &&
     s->plan->bulk_pending && (uint16_t)(s->plan->window->sent-s->plan->bulk_until)<2 &&
     (uint16_t)(s->plan->window->sent-s->plan->window->retired)<=2 ? 25:5,5,offset,zero,2,n))""")
    (out/name).write_text(s,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode")
    prepare(p.parse_args().mode)
