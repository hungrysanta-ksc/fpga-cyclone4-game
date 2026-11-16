"""Schedule CRC809 output using checked map progress and immutable scroll data."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha


def prepare(src, out, early_end=False, packed=False, defer_rows=False, overlap_maps=False,
            seal_credit=False, idle_credit=False, long_grant=False, obj_credit=False):
    assert sha(src / "obj-nes-100/firmware.stm") in {
        "f863bcf84250a5f2c202c411996ef5dcccf607076a7ba70ce5f17672ab90d05d",
        "adcb162fbbe926f3b05ac4a1b7354c21b5430301fd6c6b654100fb635dabe6b1",
    }
    out.mkdir(exist_ok=False, parents=True)
    def save(name, body):
        (out / name).write_text(body, encoding="utf-8", newline="\n")

    name = "nes_planner211.c"
    code = (src / name).read_text()
    start = code.index(" unsigned at=0;\n for(unsigned y=0;y<224;){")
    stop = code.index("\n", code.index("p->hdma_size=(uint16_t)at;", start))
    scroll = code[start:stop]
    code = once(code, scroll, "")
    code = once(code, " /* No OBJ/raw operation", scroll+"\n /* No OBJ/raw operation")
    if early_end:
        code = once(code, " /* CGRAM becomes", """ if(p->scroll_issued && resident->finish_obj && !resident->finish_obj(resident->ctx))
  return fail(p,7);
 /* CGRAM becomes""")
    if packed:
        lo = code.index("   for(unsigned x=0;x<256;x++)for(unsigned plane=0;plane<8;plane++)")
        hi = code.index("\n  }",lo)
        code = code[:lo]+"""   for(unsigned tile=0;tile<32;tile++){
    uint32_t left,right;
    memcpy(&left,pixels+tile*8,4);memcpy(&right,pixels+tile*8+4,4);
    uint8_t *dst=p->patch.chr+tile*64+slot*2;
    /* Cortex-M4 is little endian. Gather one bit from each of four bytes
     * into a nibble; the leftmost pixel occupies the most significant bit. */
    for(unsigned plane=0;plane<6;plane++){
     unsigned a=((left&0x01010101u)*0x08040201u)>>24;
     unsigned b=((right&0x01010101u)*0x08040201u)>>24;
     dst[(plane/2)*16+(plane&1)]=(uint8_t)((a<<4)|b);
     left>>=1;right>>=1;
    }
    /* All input pixels passed the <64 check; palette base 64 fixes bits 6/7. */
    dst[48]=255;
   }"""+code[hi:]
    save(name, code)

    name = "nes_native_video165.h"
    code = (src / name).read_text()
    save(name, once(code, "bool valid;uint8_t patch_count;", "bool valid;uint8_t patch_count;bool scroll_issued;"))

    name = "nes_native_sink165.c"
    code = (src / name).read_text()
    code = once(code, "op!=23 && op!=24", "op!=23 && op!=24 && op!=25")
    code = once(code, " if(op==24)op=2;", " if(op==25)op=5;\n if(op==24)op=2;")
    # As in 733, a short null DATA payload is zero. No 240-byte Flash constant.
    code = once(code,"if(op==2 && data && n>=4 && !(n&1)){\n  unsigned i=2;while(i<n && data[i]==data[i&1])i++;",
                "if(op==2 && n>=4 && !(n&1)){\n  unsigned i=n;\n  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}")
    code = once(code,"if(n)memcpy(b+16,data,n)", "if(n && data)memcpy(b+16,data,n)")
    code = once(code,"static const uint8_t zero[240]={0};","")
    code = once(code,"offset,zero,n)", "offset,NULL,n)")
    code = once(code,"static void put16", "static const uint8_t zero[2]={0};\nstatic void put16")
    if packed:
        # Reuse the span and OAM cost walks, following 729. Preserve tie-breaking.
        lo=code.index("static unsigned span_cost227(")
        hi=code.index("static bool oam227(",lo)
        helper=once(code[lo:hi],"return old<split?old:split;",
                    "return ((old<split?old:split)<<1)|(split<old);")
        code=code[:lo]+code[hi:]
        lo=code.index(" unsigned oldcost=0,newcost=0;")
        hi=code.index(" /* Synchronous immutable source:",lo)
        code=code[:lo]+" bool split=span_cost227(b,n)&1;\n"+code[hi:]
        code=once(code,"if(newcost<oldcost)count","if(split)count")
        code=once(code,"static bool span(",helper+"static bool span(")
        for term in ("b,first","b+512,32","b,544"):
            code=once(code,"span_cost227("+term+")","(span_cost227("+term+")>>1)")
    # An unsuccessful read/STOP is terminal; the bound also allows a frame
    # without a VBlank in this window to proceed through the usual SEAL path.
    marker = "  if(s->displayed && s->obj_next>=16"
    code = once(code, marker, """  if(s->displayed && s->obj_next<16){
   for(unsigned poll=0;poll<24 && !(s->plan->window->status_flags&8);poll++)
    if(!nes_window184_drain(s->plan->window,ack))return fail(s,5);
  }
"""+marker)
    if long_grant:
        code=once(code,"poll<24","poll<56")
    start = code.index("bool nes_sink527_early")
    code = code[:start]+"""bool nes_scroll810(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t map){
 /* Called after all BG rows and all scroll words are final. Skip the long
  * map drain case. Payloads are copied before the OBJ planner reuses scratch. */
 unsigned n=p->hdma_size;
 if(!n || n>240 || !(n&1) || !p->patch_count || s->plan->bank_history!=2 ||
    (((uint32_t)(map>>32)&0x7ffffu)==0x7ffffu))return true;
 if(!packet(s,24,5,0,p->hdma,n) ||
    !packet_wire(s,25,5,n,zero,2,1121-n))return false;
 p->scroll_issued=true;
 return true;
}
"""+code[start:]
    code = once(code,"if(!span(s,5,0,p->hdma,p->hdma_size))","if(!p->scroll_issued && !span(s,5,0,p->hdma,p->hdma_size))")
    code = once(code,"unsigned offset=p->hdma_size;","unsigned offset=p->scroll_issued?1121:p->hdma_size;")
    if overlap_maps:
        assert early_end and packed
        code=once(code,"(early==1||adjacent)?24:2","(early==1||early==3||adjacent)?24:2")
        code=once(code,"s->map_pair683=early==1 && count==3;break;",
                  "s->map_pair683=early==1 && count==3;if(early!=3)break;")
        code=once(code,"p->scroll_issued=true;\n return true;",
                  "p->scroll_issued=true;\n return map527(s,p,map,3);")
        code=once(code,"(span_cost227(b+512,32)>>1)","data_cost(b+512,32)")
    save(name, code)

    name = "nes_native_sink165.h"
    code = (src / name).read_text()
    save(name, once(code, "bool nes_sink527_early", "bool nes_scroll810(struct nes_native_sink165 *,struct nes_native_video165 *,uint64_t);\nbool nes_sink527_early"))
    name = "nes_native_runtime165.c"
    code = (src / name).read_text()
    code = once(code,"return nes_sink527_early(&s->sink,s->video,s->resident,final);",
                "return nes_sink527_early(&s->sink,s->video,s->resident,final) &&\n  nes_scroll810(&s->sink,s->video,s->resident->map_stale[s->resident->target]|s->video->map_dirty);")
    if seal_credit:
        # Reason 3 occurs once after a successful SEAL submission. Geometry
        # may be restored, but COMMIT still requires the previous final ACK.
        lend=("if(s->sink.bg_next==1 && s->sink.obj_next>=8)s->prefetch_left+=4;"
              if obj_credit else "s->prefetch_left+=4;")
        code=once(code,"if(reason==3)reason=2;", "if(reason==3){"+lend+"reason=2;}")
    if idle_credit:
        assert not seal_credit
        # Reason 2 before the reason-3 remap is the SEAL barrier's actual E0
        # response. An unchanged retirement cursor may lend one checked D1.
        code=once(code," if(input_wait || reason==3 || reason==4){",
                  """ if(reason==2 && !progress && !s->prefetch_left && r->ready183)
  s->prefetch_left=1;
 if(input_wait || reason==3 || reason==4){""")
    if early_end:
        code = once(code,"static bool offer527(", """/* No previous E9 has been issued. All OBJ slots are now final and END fits
 * in this same plan packet. The producer can read ROM during raw conversion. */
static bool finish_obj810(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 struct nes_plan200 *p=&s->plan;
 return p->sent || !p->count || p->count>=14 || p->bytes>208 || nes_plan200_end(p);
}
static bool offer527(""")
        code = once(code, "s->plan.bank_history=s->resident", "s->resident->finish_obj=finish_obj810;\n  s->plan.bank_history=s->resident")
        code = once(code, "bool end_ok=nes_plan200_end", "bool end_ok=s->plan.ending || nes_plan200_end")
        code = once(code, " if(reason==4 ||", """ /* Raw pixels and palette still belong to the planner during the early E9. */
 if(reason==4 && s->resident && s->resident->open && !s->resident->prepared)return check(ctx);
 if(reason==4 ||""")
    save(name, code)
    if early_end:
        name = "nes_resident211.h"
        save(name, once((src/name).read_text()," bool (*finish_bg_row)", " bool (*finish_obj)(void *);\n bool (*finish_bg_row)"))
        name = "nes_plan_service200.c"
        code = (src/name).read_text()
        private_crc = next(line for line in code.splitlines() if line.startswith("static uint16_t crc16("))
        code = once(code,private_crc,'#include "crc.h"')
        save(name, once(code,"crc16(b+4,n)","crc_xmodem_block(0xffff,b+4,n)"))
    if packed:
        name = "nes_native165.c"
        code = once((src/name).read_text(),"static const unsigned widths[8]","static const uint8_t widths[8]")
        save(name,once(code,"static const unsigned bits[6]","static const uint8_t bits[6]"))
    if defer_rows:
        from prepare_nes_lazy716 import patch_rows
        names = ("nes_planner211.c","nes_resident211.c","nes_resident211.h")
        sources = {n:((out/n) if (out/n).is_file() else (src/n)).read_text() for n in names}
        patch_rows(sources,"b")
        for name,code in sources.items():
            save(name,code)
    if overlap_maps or idle_credit or obj_credit:
        name="nes_menu_diagnostic.c"
        save(name,once((src/name).read_text(),"NES recovery failed; RESET/USB held","NES RESET/USB held"))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("src",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--early-end",action="store_true")
    p.add_argument("--packed",action="store_true")
    p.add_argument("--defer-rows",action="store_true")
    p.add_argument("--overlap-maps",action="store_true")
    p.add_argument("--seal-credit",action="store_true")
    p.add_argument("--idle-credit",action="store_true")
    p.add_argument("--long-grant",action="store_true")
    p.add_argument("--obj-credit",action="store_true",help="Lend four SEAL blocks only after one BG tile and at least eight OBJ tiles.")
    a=p.parse_args()
    if a.obj_credit and not a.seal_credit:
        p.error("--obj-credit requires --seal-credit")
    prepare(a.src,a.out,a.early_end,a.packed,a.defer_rows,a.overlap_maps,a.seal_credit,a.idle_credit,a.long_grant,a.obj_credit)
