# SPDX-License-Identifier: MIT
"""Bound terminal source service and reduce the last geometry block's raster restore cost."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha

BASE_ELF = "698635c3b374b760236d4926395c3d75b24a62146a8c808495faad18166b2838"
MODES = (
    "raster", "handoff", "combined", "groups", "wire_rows", "wire_batch",
    "wire_fit", "wire_credit", "rom_wait", "rom_seal", "packed", "packed_wait",
    "counts", "counts_wait", "lane", "lane_wait", "lane_mask", "lane_mask_seal",
)


def share_section_order(source):
    order = "while(s->next_kind<6&&s->at[s->next_kind]==s->counts[s->next_kind])s->next_kind++;"
    source = once(source, order, "advance_kind(s);")
    source = once(source, "static bool logical_record(",
                  "static void advance_kind(struct nes_native165 *s){"+order+"}\nstatic bool logical_record(")
    source = once(source, "case 1:if((v>>3)>=s->counts[0]/33u)return fail(s,10);s->rows[index]=(uint8_t)v;break;", "")
    source = once(source, "case 5:s->palette[index]=(uint8_t)v;break;", "")
    return source


def receiver(source, mode):
    source = once(source, """for(unsigned i=0;i<n;i++){
   if(!logical_record(s,4,gen,start+i,v))return false;
   v=raster_next471(v);
  }""", """if(!logical_record(s,4,gen,start,v))return false;
  /* Each successor changes only the low scroll bits. The checked first
   * row proves the common palette, section order and source identity. */
  for(unsigned i=1;i<n;i++){v=raster_next471(v);s->raster[start+i]=v;}
  s->at[4]+=n-1;s->records+=n-1;""")
    if mode == "groups":
        source = once(source, """for(unsigned i=0;i<n;i++)if(!logical_record(s,k,gen,start+i,(v>>(8*(n-1-i)))&255))return false;""",
                          """if(!logical_record(s,k,gen,start,(v>>(8*(n-1)))&255))return false;
  uint8_t *dst=k==1?s->rows:s->palette;
  unsigned limit=k==1?8*(s->counts[0]/33u):64;
  for(unsigned i=n-1;i;i--){uint8_t x=v;if(x>=limit)return fail(s,k==1?10:9);dst[start+i]=x;v>>=8;}
  s->at[k]+=n-1;s->records+=n-1;""")
    if mode in ("wire_rows", "wire_batch", "wire_fit", "wire_credit"):
        source = share_section_order(source)
        # These two packed kinds have one legal wire encoding. Read the
        # original big-endian lane directly, including all leading padding.
        source = once(source, "unsigned index,uint64_t v){\n if(kind==6",
                      "unsigned index,uint64_t v,const uint8_t *lane){\n if(kind==6")
        source = once(source, "||n!=(left>8?8:left)||(n<8 && v>>(8*n))", "||n!=(left>8?8:left)")
        source = once(source, "for(unsigned i=0;i<n;i++)if(!logical_record(s,k,gen,start+i,(v>>(8*(n-1-i)))&255))return false;", """for(unsigned i=0;i<8-n;i++)if(lane[i])return fail(s,33);
  advance_kind(s);
  if(k!=s->next_kind)return fail(s,9);
  uint8_t *dst=k==1?s->rows:s->palette;
  unsigned limit=k==1?(s->counts[0]/33u)*8u:64u;
  for(unsigned i=8-n;i<8;i++){
   if(lane[i]>=limit)return fail(s,k==1?10:9);
   dst[s->at[k]++]=lane[i];s->records++;
  }""")
        source = once(source, "uint64_t value=0;for(unsigned j=0;j<width;j++)value=(value<<8)|p[pos++];",
                      """const uint8_t *lane=p+pos;pos+=width;
  uint64_t value=0;
  if(kind!=7 || ((index>>8)!=0x19 && (index>>8)!=0x1d))
   for(unsigned j=0;j<width;j++)value=(value<<8)|lane[j];""")
        source = once(source, "if(!record(s,kind,gen,index,value))", "if(!record(s,kind,gen,index,value,lane))")
    if mode in ("wire_fit", "wire_credit"):
        begin = source.index("static unsigned need(")
        end = source.index("static void advance_kind(", begin)
        source = '#pragma GCC optimize ("Oz")\n' + source[:begin] + """static void require_tile(struct nes_native165 *s,unsigned tag,unsigned kind){
 uint8_t *entry=&s->required[tag>>2];
 unsigned shift=(tag&3)*2;
 if(!(*entry&(3u<<shift)))s->missing++;
 *entry|=(uint8_t)(kind<<shift);
}
""" + source[end:]
    if mode in ("packed", "packed_wait", "counts", "counts_wait", "lane", "lane_wait", "lane_mask", "lane_mask_seal"):
        # Packed literals are right-aligned in an already checked 64-bit
        # value. Inspect bytes in wire order. The first invocation validates
        # section order and width; preserve prefix state on a bad later byte.
        source = once(source, "for(unsigned i=0;i<n;i++)if(!logical_record(s,k,gen,start+i,(v>>(8*(n-1-i)))&255))return false;", """const uint8_t *bytes=(const uint8_t *)&v;
  if(!logical_record(s,k,gen,start,bytes[n-1]))return false;
  uint8_t *dst=k==1?s->rows:s->palette;
  unsigned limit=k==1?(s->counts[0]/33u)*8u:64u;
  while(--n){unsigned x=bytes[n-1];if(x>=limit)return fail(s,k==1?10:9);
   dst[s->at[k]++]=(uint8_t)x;s->records++;
  }""")
        # Both consumers verify the original cached CRC. An uncached D0 is
        # verified by query785 itself, so one helper owns the status check.
        source = once(source, "bool nes_native165_poll(", """static bool current791(struct nes_native165 *s,nes_native165_transfer_fn fn,void *ctx,uint8_t *rx){
 if(!s->ready183)return query785(s,fn,ctx,rx);
 memcpy(rx,s->status183,8);s->ready183=false;
 return status(rx);
}
bool nes_native165_poll(""")
        source = once(source, """if(s->ready183){memcpy(rx,s->status183,8);s->ready183=false;}
 else if(!query785(s,fn,ctx,rx))return fail(s,21);
 if(!status(rx))return fail(s,21);""", "if(!current791(s,fn,ctx,rx))return fail(s,21);")
        source = once(source, """if(s->ready183){
  memcpy(rx,s->status183,8);s->ready183=false;
  if(!status(rx))return fail(s,25);
 }else if(!query785(s,fn,ctx,rx))return fail(s,25);""", "if(!current791(s,fn,ctx,rx))return fail(s,25);")
    if mode in ("lane", "lane_wait", "lane_mask", "lane_mask_seal"):
        source = share_section_order(source)
        begin = source.index("  const uint8_t *bytes=(const uint8_t *)&v;")
        end = source.index(" }else return fail(s,33);", begin)
        source = source[:begin] + """  advance_kind(s);
  if(s->next_kind!=k)return fail(s,9);
  unsigned limit=k==1?(s->counts[0]/33u)*8u:64u;
  uint8_t *dst=(k==1?s->rows:s->palette)+start;
  unsigned i=0;
  for(;i<n;i++){
   unsigned byte=((const uint8_t *)&v)[n-1-i];
   if(byte>=limit)break;
   dst[i]=(uint8_t)byte;
  }
  s->at[k]+=i;s->records+=i;
  if(i!=n)return fail(s,k==1?10:9);
""" + source[end:]
    if mode in ("lane_mask", "lane_mask_seal"):
        lo = source.index("static unsigned need(")
        hi = source.index("static void advance_kind(", lo)
        source = source[:lo] + """static void require_tile(struct nes_native165 *s,unsigned tag,unsigned kind){
 uint8_t *entry=&s->required[tag>>2];
 unsigned shift=(tag&3u)*2u,old=*entry;
 s->missing+=!((old>>shift)&3u);
 *entry=(uint8_t)(old|(kind<<shift));
}
""" + source[hi:]
    if mode in ("counts", "counts_wait"):
        for error in (7, 30):
            source = once(source, f"for(unsigned k=0;k<6;k++)if(s->at[k]!=s->counts[k])return fail(s,{error});",
                          f"if(memcmp(s->at,s->counts,sizeof s->at))return fail(s,{error});")
        start = source.index("static unsigned need(")
        end = source.index("static bool logical_record(", start)
        source = source[:start] + """static void require_tile(struct nes_native165 *s,unsigned tag,unsigned kind){
 unsigned shift=(tag&3u)*2u;
 uint8_t *bits=s->required+(tag>>2);
 if(!(*bits&(3u<<shift)))s->missing++;
 *bits|=(uint8_t)(kind<<shift);
}
""" + source[end:]
    return source


def wait_policy(source, mode):
    if mode == "lane_mask_seal":
        source = once(source, "  s->prefetch_left=1;", "  s->prefetch_left=3;")
        # Recheck the output ACK when the last confirmed D0 had no next
        # input. Do not issue a second empty D0 or manufacture a token.
        source = once(source, "   if(reason!=2)break;", "   if(reason!=2 || !r->ready183)break;")
    if mode in ("rom_wait", "rom_seal", "packed_wait", "counts_wait", "lane_wait"):
        source = once(source, """bool input_wait=reason==0 ? s->plan.finished : reason==1 && !progress &&
    (s->plan.finished || (s->resident && s->resident->prepared && s->plan.ending));""",
                      """bool input_wait=(reason==0 && s->plan.finished) || (reason<=1 && !progress &&
    (s->plan.finished || (s->resident && s->resident->prepared && s->plan.ending)));""")
        if mode in ("rom_seal", "counts_wait", "lane_wait"):
            source = once(source, "  s->prefetch_left=1;", "  s->prefetch_left=3;")
    if mode == "wire_credit":
        source = once(source, "  s->prefetch_left=1;",
                      "  s->prefetch_left=r->status183[5]==0 && r->status183[6]<=128 ? 2 : 1;")
    if mode in ("handoff", "combined", "groups", "wire_batch"):
        # Once a checked status reports another input block and a SEAL is
        # outstanding, finish a short geometry tail without another E0.
        # STOP is checked before, between, and within the three transactions.
        source = once(source, "  s->prefetch_left=1;",
                      "  s->prefetch_left=r->next_kind>=2 ? 3 : 1;")
    return source


def prepare(base, out, mode):
    assert sha(base / "obj-nes-100/sd2snes.elf") == BASE_ELF
    out.mkdir(parents=True, exist_ok=False)
    for name, adjust in (("nes_native165.c", receiver), ("nes_native_runtime165.c", wait_policy)):
        original = (base / name).read_text()
        if name == "nes_native165.c" and mode == "handoff":
            continue
        updated = adjust(original, mode)
        if updated != original:
            (out / name).write_text(updated, newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("mode", choices=MODES)
    args = parser.parse_args()
    prepare(args.base, args.out, args.mode)
