# SPDX-License-Identifier: MIT
"""Shorten the checked input decode and arbitrate small ready tiles after map credit."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out, mode):
    assert sha(base / "obj-nes-100/sd2snes.elf") == "ca8107c7724637af422211e72032399c039a1767a45c1f65c9ee18a03f035a0d"
    out.mkdir(parents=True, exist_ok=False)
    name = "nes_native165.c"
    s = (base / name).read_text()
    s = once(s, "static const unsigned widths[8]", "static const uint8_t widths[8]")
    # Extract the low six bits each time, with the same width/padding check.
    s = once(s, "for(unsigned i=0;i<n;i++)s->raw_pixels[start+i]=(uint8_t)(colors>>(6*(n-1-i)))&63;",
             "for(unsigned i=n;i;i--){s->raw_pixels[start+i-1]=(uint8_t)colors&63;colors>>=6;}")
    if mode in ("compact_rows", "compact_raster"):
        s = '#pragma GCC optimize ("Oz")\n'+s
        start=s.index("static unsigned need(")
        end=s.index("static bool logical_record(",start)
        s=s[:start]+"""static void require_tile(struct nes_native165 *s,unsigned tag,unsigned kind){
 uint8_t *entry=&s->required[tag>>2];
 unsigned shift=(tag&3)*2;
 if(!(*entry&(3u<<shift)))s->missing++;
 *entry|=(uint8_t)(kind<<shift);
}
"""+s[end:]
    if mode in ("packed", "packed_tile"):
        # Keep one logical_record per byte and the original bounds; consume
        # a left-aligned lane using constant shifts on the Cortex-M4.
        s = once(s, "for(unsigned i=0;i<n;i++)if(!logical_record(s,k,gen,start+i,(v>>(8*(n-1-i)))&255))return false;",
                 """v<<=8*(8-n);
  for(unsigned i=0;i<n;i++){
   if(!logical_record(s,k,gen,start+i,v>>56))return false;
   v<<=8;
  }""")
    if mode in ("rows", "rows_raster", "compact_rows", "compact_raster"):
        # Literal and repeated row/palette records are already rejected by
        # record(). Their sole valid ingress is the packed 1..8 byte form.
        old = """while(s->next_kind<6&&s->at[s->next_kind]==s->counts[s->next_kind])s->next_kind++;"""
        s = once(s, old, "advance_kind(s);")
        s = once(s, "static bool logical_record(", "static void advance_kind(struct nes_native165 *s){"+old+"}\nstatic bool logical_record(")
        s = once(s, "case 1:if((v>>3)>=s->counts[0]/33u)return fail(s,10);s->rows[index]=(uint8_t)v;break;", "")
        s = once(s, "case 5:s->palette[index]=(uint8_t)v;break;", "")
        s = once(s, "for(unsigned i=0;i<n;i++)if(!logical_record(s,k,gen,start+i,(v>>(8*(n-1-i)))&255))return false;",
                 """advance_kind(s);
  if(k!=s->next_kind)return fail(s,9);
  unsigned limit=k==1?8u*(s->counts[0]/33u):64u;
  uint8_t *dst=k==1?s->rows:s->palette;
  v<<=8*(8-n);
  for(unsigned i=0;i<n;i++,v<<=8){
   unsigned b=(unsigned)(v>>56);
   if(b>=limit)return fail(s,k==1?10:9);
   dst[start+i]=(uint8_t)b;s->at[k]++;s->records++;
  }""")
    if mode in ("raster", "both", "bytes", "joint", "rows_raster", "compact_raster"):
        # raster_next471 changes only the low 15 bits. Geometry, palette and
        # state validation is identical for every following member of this run.
        s = once(s, """for(unsigned i=0;i<n;i++){
   if(!logical_record(s,4,gen,start+i,v))return false;
   v=raster_next471(v);
  }""", """if(!logical_record(s,4,gen,start,v))return false;
  for(unsigned i=1;i<n;i++){
   v=raster_next471(v);
   s->raster[start+i]=v;
  }
  s->at[4]+=n-1;s->records+=n-1;""")
    if mode in ("bytes", "joint"):
        # Packed rows and palette always use one byte per value. The first
        # record performs the phase transition. Check every subsequent value,
        # and advance counts only after its bytes have been validated.
        s = once(s, "for(unsigned i=0;i<n;i++)if(!logical_record(s,k,gen,start+i,(v>>(8*(n-1-i)))&255))return false;",
                 """uint8_t *dst=k==1?s->rows:s->palette;
  unsigned limit=k==1?8u*(s->counts[0]/33u):64u;
  if(!logical_record(s,k,gen,start,(uint8_t)(v>>(8*(n-1)))))return false;
  for(unsigned i=n-1;i;i--){
   unsigned byte=(uint8_t)v;
   if(byte>=limit)return fail(s,k==1?10:9);
   dst[start+i]=(uint8_t)byte;v>>=8;
  }
  s->at[k]+=n-1;s->records+=n-1;""")
    (out / name).write_text(s, newline="\n")
    if mode in ("batch", "tail", "batch_tile", "resume", "resume_tile"):
        name = "nes_native_runtime165.c"
        s = (base / name).read_text()
        budget = "r->next_kind==7 ? 3 : 1" if mode == "tail" else "3"
        s = once(s, "  s->prefetch_left=1;", "  s->prefetch_left="+budget+";")
        s = once(s, "   if(reason!=2)break;",
                 """   if(reason!=2)break;
   if(!r->ready183){s->prefetch_left=0;break;}""")
        if mode in ("resume", "resume_tile"):
            # A temporary empty source does not spend the unconsumed part of
            # the original seven-block reservation; recheck on the next wait.
            s = once(s, "if(!r->ready183){s->prefetch_left=0;break;}", "if(!r->ready183)break;")
        (out / name).write_text(s, newline="\n")
    if mode in ("sealed_poll", "rearm"):
        name = "nes_native_runtime165.c"
        s = once((base / name).read_text(), " return nes_cost474_pause(ctx,check,reason,progress);",
                 """ if(reason==2 && r->ready183 && r->state==NES_NATIVE165_COMPLETE)return check(ctx);
 return nes_cost474_pause(ctx,check,reason,progress);""")
        (out / name).write_text(s, newline="\n")
    if mode == "rearm":
        name = "nes_plan_service200.c"
        s = once((base / name).read_text(), "if(flags&2){p->finished=true;return true;}",
                 "if(flags&2){if(flags!=2)return fail(p,4);p->finished=true;return true;}")
        start=s.index(" uint8_t rx[20];bool sent=false;")
        end=s.index("   p->sent=0;",start)
        send=s[s.index("   uint8_t cmd[7]",start):s.index("   sent=true;",start)]
        s=s[:start]+send+""" uint8_t rx[20];
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!p->guard(p->ctx))return fail(p,2);
  const uint8_t phase=NES_PLAN215_REARM;
  if(!read509(p,rx,phase))return false;
  if(rx[3]&0xf8)return status215(p,phase,NES_PLAN215_FLAGS,rx);
  for(unsigned k=6;k<19;k++)if(rx[k])return status215(p,phase,NES_PLAN215_EMPTY,rx);
  unsigned accepted=(unsigned)rx[4]*256+rx[5];
  if(rx[3]==1&&accepted==0){
"""+s[end:]
        (out / name).write_text(s, newline="\n")
    if mode == "finish":
        # A checked empty END makes the input head visible. Offer one block
        # before ordinary output, subject to the existing resident release.
        name = "nes_plan_service200.c"
        s = once((base / name).read_text(),
                 "if(flags&2){p->finished=true;return true;}",
                 "if(flags&2){p->finished=true;return wait485(p);}")
        (out / name).write_text(s, newline="\n")
    if mode in ("tile", "both", "joint", "batch_tile", "packed_tile", "resume_tile"):
        name = "nes_plan_service200.c"
        s = (base / name).read_text()
        # Let a single BG or OBJ tile take a queue slot immediately. The
        # descriptor validation, credit limit and receipt remain in submit.
        s = once(s, "if(p->ending && p->bank_history==2 && (p->window->last[1]==2",
                 "if((d[3] || d[2]>(d[1]?32:16)) && p->ending && p->bank_history==2 && (p->window->last[1]==2")
        (out / name).write_text(s, newline="\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("base", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("mode", choices=("raw", "raster", "tile", "both", "bytes", "joint", "batch", "tail", "batch_tile", "packed", "packed_tile", "finish", "resume", "resume_tile", "rows", "rows_raster", "sealed_poll", "rearm", "compact_rows", "compact_raster"))
    a = p.parse_args()
    prepare(a.base, a.out, a.mode)
