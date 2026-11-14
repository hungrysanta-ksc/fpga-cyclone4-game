# SPDX-License-Identifier: MIT
"""Build MMC763 derivatives with bounded source refill and checked right-page map gaps."""
import argparse
from pathlib import Path
from nes_raw506 import once
from pack_nes_report782 import pack_reports
from prepare_nes_supply781 import prepare as supply


def prepare(base, out, map_gap, retry_rows=False, tile_then_map=False, connected_fixture=False):
    supply(base, out, obj_first=True, refill=True)
    def read(name):
        path=out/name
        return (path if path.exists() else base/name).read_text()
    def write(name, text):
        (out/name).write_text(text,newline="\n")

    name="nes_native_runtime165.c"
    s=read(name)
    # Compare the two observed OAM workloads using a frame-independent
    # threshold. Both orders keep the same rank and slot checks.
    s=once(s,"s->plan.bank_history==2?tile_boundary781", "s->plan.bank_history==2 && r->counts[2]<=24?tile_boundary781")
    # A verified positive D0 allows an extra D1 immediately. An empty
    # status gets the normal E0/STOP service instead of an extra transaction.
    s=once(s,"r->state==NES_NATIVE165_RECEIVING && s->transport.last","r->ready183 && r->state==NES_NATIVE165_RECEIVING && s->transport.last")
    write(name,s)
    name="nes_native_sink165.c"
    s=read(name)
    s=once(s,'if(op==2 && data && n>=4 && !(n&1)){\n  unsigned i=2;while(i<n && data[i]==data[i&1])i++;',
          'if(op==2 && n>=4 && !(n&1)){\n  unsigned i=n;\n  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}')
    s=once(s,'put16(b+12,n);if(n)memcpy','put16(b+12,n);if(n && data)memcpy')
    s=once(s,'zero[240]={0}','zero[2]={0}')
    s=once(s,'else if(!packet(s,2,5,offset,zero,n))','else if(!packet(s,2,5,offset,NULL,n))')
    if retry_rows:
        # On an OBJ-first warm frame a ready first tile may win the first
        # offer. Later row callbacks have their own completed 3-row frontier.
        # Recheck the real credit; never advance map_next on a rejected offer.
        s=once(s,"if(!ready){if(!s->map_next)s->map_next=128;return true;}",
               "if(!ready){if(!s->map_next && !r->tile_boundary)s->map_next=128;return true;}")
    if tile_then_map:
        # Bind the offer to a real tile receipt/submission in this poll.
        # A stale repeated or absent descriptor alone cannot bypass tile arbitration.
        s=once(s,"  bool ready;\n  if(!nes_plan527_map_credit","  bool ready;\n  uint16_t sent=s->plan->window->sent;\n  if(!nes_plan527_map_credit")
        s=once(s,"  if(!ready){if(!s->map_next && !r->tile_boundary)","""  if(!ready && r->tile_boundary && sent!=s->plan->window->sent &&
     !nes_window532_room(s->plan->window,&ready))return false;
  if(!ready){if(!s->map_next && !r->tile_boundary)""")
    if map_gap:
        s=once(s," for(unsigned g=s->map_next&127;g<64;){"," bool short_right_tail=false;\n for(unsigned g=s->map_next&127;g<64;){")
        s=once(s,"  pair=pairable && count==3 && s->map_pair683;","  short_right_tail=first>=32 && count<3;\n  pair=pairable && count==3 && s->map_pair683;")
        s=once(s,'  if(!((mask>>g)&1)){g++;pair=false;continue;}','''  if(!((mask>>g)&1)){g++;pair=false;continue;}
  /* A right-page short tail precedes a disjoint run. Retire its actual
   * head first. Give the idle DMA a bounded opportunity while the next
   * map packet is still private. The progress bit grants no identity. */
  if(!early && short_right_tail && !((mask>>(g-1))&1) && pairable && s->plan->ending &&
     s->plan->window->last[1]==2 &&
     (s->plan->window->last[0]==2 || s->plan->window->last[0]==4)){
   struct nes_sink_window184 *w=s->plan->window;
   uint8_t ack[12];
   for(unsigned i=0;i<12;i++){
    if(!nes_window184_drain(w,ack))return false;
    if((w->status_flags&8) || !w->wait)break;
    if(!w->wait(w->ctx,w->guard,0,false))return false;
   }
  }''')
    if connected_fixture:
        # Reproduce the intermediate full-link control with a permanently attached plan.
        s=once(s," && pairable && s->plan->ending &&\n     s->plan->window->last[1]==2",
               " && s->plan->ending &&\n     s->plan->bank_history==2 && s->plan->window->last[1]==2")
    write(name,s)
    name="nes_plan_service200.c"
    s=read(name)
    start=s.index("static uint16_t crc16(")
    s=s[:start]+'#include "crc.h"\n'+s[s.index("static bool fail(",start):]
    s=once(s,"crc16(b+4,n)","crc_xmodem_block(65535,b+4,n)")
    write(name,s)
    pack_reports(read,write)
    # Cold and post-session paths stay fully linked, with full diagnostics.
    for name in ("nes_h1_stm32.c","nes_menu_diagnostic.c","nes_budget210.c","nes_rom_verify.c","nes_h1_session.c","nes_cost471.c","nes_plan191.c","nes_native_sink165.c","nes_plan_service200.c","nes_native_runtime165.c","nes_planner211.c"):
        write(name,'#pragma GCC optimize ("Oz")\n'+read(name))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("src",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--map-gap",action="store_true")
    p.add_argument("--retry-rows",action="store_true")
    p.add_argument("--tile-then-map",action="store_true")
    p.add_argument("--connected-fixture",action="store_true",help="reproduce the intermediate connected-plan control")
    a=p.parse_args()
    if a.connected_fixture and (not a.map_gap or a.retry_rows):
        p.error("--connected-fixture requires --map-gap alone")
    if a.tile_then_map and not a.retry_rows:
        p.error("--tile-then-map needs --retry-rows")
    prepare(a.src,a.out,a.map_gap,a.retry_rows,a.tile_then_map,a.connected_fixture)
