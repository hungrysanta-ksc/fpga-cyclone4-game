# SPDX-License-Identifier: MIT
"""Publish a checked prefix of the completed warm map at the tile END boundary."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out, lend, reuse=False, first=False, defer=False, idle=False, small=False, scoped=False):
    assert sha(base/"obj-nes-100/sd2snes.elf")=="7193456ca235672c4f116bd30581a1a3b81fadf7f822e95ad9b092ad52ff0a87"
    out.mkdir(parents=True,exist_ok=False)
    name="nes_native_runtime165.c"
    s=(base/name).read_text()
    s=once(s," return end ? nes_plan200_end(&s->plan) : nes_plan549_first(&s->plan);",""" if(!end)return nes_plan549_first(&s->plan);
 if(!nes_plan200_end(&s->plan))return false;
 /* BG rows and slots are now immutable. Keep input owned until prepare.
  * Only split when a sparse right page has a later run; dense uploads
  * keep the original quiet-map / tile supply schedule. */
 uint64_t mask=s->resident->map_stale[s->resident->target]|s->video->map_dirty;
 unsigned right=(unsigned)(mask>>32);
 if(right && (right&(right+(right&-right))))
  return map527(&s->sink,s->video,mask,3);
 return true;""")
    if scoped:
        s=once(s,"if(right && (right&(right+(right&-right))))",
               "if(s->plan.bulk[1] && s->plan.bulk[2]==32 && !s->plan.bulk[3] && right && (right&(right+(right&-right))))")
    (out/name).write_text(s,newline="\n")
    name="nes_native_sink165.c"
    s=(base/name).read_text()
    s=once(s,"bool short_right_tail=false;","bool short_right_tail=!early && s->map_next>128;")
    s=once(s,"if(early){s->map_next=", """if(early==3){
   s->map_next=(uint8_t)g;
   if(short_right_tail && g<64 && !((mask>>g)&1)){
    s->map_next|=128;break;
   }
   continue;
  }
  if(early){s->map_next=""")
    if first:
        # Retry a single skipped left-page offer once a tile really owns
        # its token. A fresh guard and checked E1 credit still own submission.
        # Preserve the high cursor mark so later row callbacks wait for END.
        s=once(s," if(s->map_next>=64)return true;", """ if(s->map_next==128 && !final && r->tile_boundary && s->plan->bulk_pending &&
    (uint16_t)(s->plan->window->sent-s->plan->window->retired)<3){
  uint32_t left=(uint32_t)(r->map_stale[r->target]|p->map_dirty);
  if(!map527(s,p,left,1))return false;
  s->map_next|=128;
 }
 if(s->map_next>=64)return true;""")
    if defer:
        # A warm blocked early offer has published no map yet. If the first
        # left and right dirty runs each contain four rows, postpone the first
        # left run. Record its start + 1 in existing padding, then emit it
        # exactly once after the right handoff and before any later span.
        header="nes_native_sink165.h"
        (out/header).write_text(once((base/header).read_text(),"bool map_pair683;",
            "bool map_pair683; uint8_t deferred783;"),newline="\n")
        s=once(s,"s->map_next=0;s->map_pair683=false;","s->map_next=s->deferred783=0;s->map_pair683=false;")
        s=once(s," bool short_right_tail=!early && s->map_next>128;", """ unsigned cursor=s->map_next&127;
 if(early==3 && s->map_next==128 && (uint32_t)mask){
  unsigned first=__builtin_ctz((uint32_t)mask);
  unsigned right=(unsigned)(mask>>32);
  if(first<=27 && ((mask>>first)&31)==15 && right && ((right>>__builtin_ctz(right))&31)==15){
   cursor=first+4;s->deferred783=(uint8_t)(first+1);
  }
 }
 bool short_right_tail=!early && s->map_next>128;""")
        s=once(s,"for(unsigned g=s->map_next&127;g<64;)", "for(unsigned g=cursor;g<64;)")
        # Emit the postponed pair after the real right-run drain. The
        # second call at loop exit handles a short tail at the end of the mask.
        marker="bool map527("
        helper="""static bool deferred783(struct nes_native_sink165 *s,struct nes_native_video165 *p){
 if(!s->deferred783)return true;
 unsigned at=(s->deferred783-1)*64;
 s->deferred783=0;
 return packet(s,2,2,at,p->map+at,192) && packet(s,2,2,at+192,p->map+at+192,64);
}
"""
        s=once(s,marker,helper+marker)
        s=once(s,"  unsigned first=g++,count=1;","  if(!early && !deferred783(s,p))return false;\n  unsigned first=g++,count=1;")
        s=once(s," return true;\n}\nbool nes_sink527_early"," return early || deferred783(s,p);\n}\nbool nes_sink527_early")
    if idle:
        # One sticky progress sample cannot prove all five destinations.
        # While a postponed pair exists, keep serving STOP/input after the
        # first hint through the same bounded loop; final ACK is unchanged.
        s=once(s,"if((w->status_flags&8) || !w->wait)break;",
               "if(!w->wait || ((w->status_flags&8) && !s->deferred783))break;")
    if small or scoped:
        s=once(s,"((mask>>first)&31)","(((uint32_t)mask>>first)&31)")
    if small:
        s=once(s,"if(early==3 && s->map_next==128 && (uint32_t)mask)",
               "if(early==3 && s->map_next==128 && s->plan->bulk[1] && !((s->plan->bulk[2]^32)|s->plan->bulk[3]) && (uint32_t)mask)")
    # A suspended short right run may end directly before an empty row.
    # g>0 is guaranteed by the original short run or a marked cursor.
    (out/name).write_text(s,newline="\n")
    if reuse:
        # Keep retrying later row frontiers only on the OBJ-first path.
        sink=out/name
        s=once(sink.read_text(),"if(!ready){if(!s->map_next)s->map_next=128;",
               "if(!ready){if(!s->map_next && !r->tile_boundary)s->map_next=128;")
        sink.write_text(s,newline="\n")
    if lend or reuse:
        name="nes_plan_service200.c"
        s=(base/name).read_text()
        # Repeated ownership is already verified in poll. When a preceding
        # bulk is still owed, the existing send/through paths retain its
        # receipt. Reserve a queue slot before lending a MAP to that owner.
        if lend:
            s=once(s,"  return complete485(p);\n }\n uint8_t flags;", """  if(p->bulk_pending && (uint16_t)(p->window->sent-p->bulk_until)<2 &&
     (uint16_t)(p->window->sent-p->window->retired)<3)return true;
  return complete485(p);
 }
 uint8_t flags;""")
        if reuse:
            s=once(s," uint8_t flags;\n *ready=false;"," uint8_t flags;\n uint16_t sent=p->window->sent;\n *ready=false;")
            s=once(s," *ready=!(flags&4);",""" /* A repeated fully validated descriptor already has a submission.
  * Real E0 room leaves one queue slot reserved; bulk_until is still owed.
  * A newly submitted descriptor always wins this opportunity. */
 *ready=!(flags&4);
 if(!*ready && p->bulk_valid && p->bank_history==2 && p->window->sent==sent)
  return nes_window532_room(p->window,ready);""")
        (out/name).write_text(s,newline="\n")

    if first or defer:
        # Use the same CRC-8 polynomial, initial value and checked boundaries
        # for E0, E8/E9 and D0. Full identity and range checks are unchanged.
        impl="nes_native165.c"
        text=(base/impl).read_text().replace("static uint8_t crc8(","uint8_t nes_crc783(").replace("crc8(","nes_crc783(")
        (out/impl).write_text(text,newline="\n")
        proto="uint8_t nes_crc783(const uint8_t *,unsigned);"
        for name in ("nes_sink_window184.c","nes_plan_service200.c"):
            source=out/name
            s=(source if source.exists() else base/name).read_text()
            fn=next(line for line in s.splitlines() if line.startswith("static uint8_t crc8("))
            s=once(s,fn,proto)
            if name=="nes_sink_window184.c":
                s=once(s,"uint8_t c=0;for(unsigned i=1;i<19;i++)c=crc8(c,rx[i]);","uint8_t c=nes_crc783(rx+1,18);")
            source.write_text(s.replace("crc8(","nes_crc783("),newline="\n")

    if defer:
        # The remaining multiline boot diagnostic is plain ASCII in 782D.
        # Encode it using the existing immutable report dictionary.
        import ast
        import re
        from prepare_nes_report594 import literal
        name="nes_budget210.c"
        s=(base/name).read_text()
        pattern=r'(nes_report_packed782\(text,size,n,\s*)("(?:\\.|[^"\\])*"\s*"(?:\\.|[^"\\])*")'
        m=re.search(pattern,s)
        seq=re.findall(r'"(?:\\.|[^"\\])*"',m[2])
        plain=b"".join(ast.literal_eval(v).encode("ascii") for v in seq)
        pairs=ast.literal_eval(re.search(r'static const unsigned char pairs782\[\] = (".*");',s)[1]).encode("latin1")
        assert len(plain)==283 and len(pairs)==256
        data=plain
        for i in range(0,len(pairs),2):
            data=data.replace(pairs[i:i+2],bytes([128+i//2]))
        assert len(data)==126
        (out/name).write_text(s[:m.start(2)]+literal(data)+s[m.end(2):],newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("base",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--lend-credit",action="store_true")
    p.add_argument("--repeat-room",action="store_true")
    p.add_argument("--first-left",action="store_true")
    p.add_argument("--defer-first",action="store_true")
    p.add_argument("--idle-window",action="store_true")
    p.add_argument("--small-obj",action="store_true")
    p.add_argument("--scoped-end",action="store_true")
    a=p.parse_args()
    if a.scoped_end and not a.defer_first:p.error("--scoped-end requires --defer-first")
    if a.small_obj and not a.defer_first:p.error("--small-obj requires --defer-first")
    if a.idle_window and not a.defer_first:p.error("--idle-window requires --defer-first")
    if a.first_left and a.defer_first:p.error("choose one prefix variant")
    prepare(a.base,a.out,a.lend_credit,a.repeat_room,a.first_left,a.defer_first,a.idle_window,a.small_obj,a.scoped_end)
