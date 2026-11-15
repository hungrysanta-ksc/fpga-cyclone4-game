# SPDX-License-Identifier: MIT
"""Time checked RETIRE and the following COMMIT on the linked 789E firmware."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha

BASE = "0a657903bf8c48dcc3cafd801115884ed88e16889e81cef97655f6082a1d579f"


def prepare(base, out, mode):
    assert sha(base / "obj-nes-100/sd2snes.elf") == BASE
    out.mkdir(parents=True, exist_ok=False)
    if mode in ("retire", "both", "bridge_retire", "fixed_retire"):
        # FINISH already checks the CRC, accepted count and all descriptor bytes.
        # Require exactly DONE. EA still requires a checked display ACK; its
        # own generation/count must be accepted before REARM can succeed.
        name = "nes_plan_service200.c"
        s = (base / name).read_text()
        s = once(s, "if(flags&2){p->finished=true;return true;}",
                 "if(flags&2){if(flags!=2)return fail(p,4);p->finished=true;return true;}")
        lo = s.index(" uint8_t rx[20];bool sent=false;")
        hi = s.index("   p->sent=0;", lo)
        send = s[s.index("   uint8_t cmd[7]", lo):s.index("   sent=true;", lo)]
        s = s[:lo] + send + """ uint8_t rx[20];
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!p->guard(p->ctx))return fail(p,2);
  const uint8_t phase=NES_PLAN215_REARM;
  if(!read509(p,rx,phase))return false;
  if(rx[3]&0xf8)return status215(p,phase,NES_PLAN215_FLAGS,rx);
  for(unsigned k=6;k<19;k++)if(rx[k])return status215(p,phase,NES_PLAN215_EMPTY,rx);
  unsigned accepted=(unsigned)rx[4]*256+rx[5];
  if(rx[3]==1&&accepted==0){
""" + s[hi:]
        (out / name).write_text(s, newline="\n")
    if mode in ("ready", "both", "owned_ready"):
        name = "nes_native_runtime165.c"
        s = (base / name).read_text()
        # prepare has verified the returned D0 CRC. Poll consumes the held
        # status once and checks the actual D1 CRC, D2 and confirming D0.
        s = once(s, " }else if(r->state!=NES_NATIVE165_COMMITTED){",
                 " }\n if(r->state!=NES_NATIVE165_COMMITTED){")
        (out / name).write_text(s, newline="\n")

    if mode in ("raw_bridge", "bridge_retire", "raw_planes"):
        name = "nes_native_sink165.c"
        s = (base / name).read_text()
        old = "  if(!span(s,5,offset,raw,packed))return false;"
        if mode == "raw_planes":
            new = """  if(packed==384){
   for(unsigned at=0;at<packed;at+=192)
    if(!packet(s,2,5,offset+at,raw+at,192))return false;
  }else if(!span(s,5,offset,raw,packed))return false;"""
            s = once(s, old, new)
        else:
            # Combine literal + short repeat + tiny literal into one legacy
            # DATA frame. OAM's wire-price function has no new policy.
            old = "  bool ok=count>240?"
            new = """  if(section==5 && offset==1121 && n==384 && newcost<oldcost &&
     count>=4 && repeat_bytes(b+at,count)<count){
   unsigned rest=n-at-count;
   if(rest>=64){
    unsigned run=repeat_bytes(b+at+count,rest);
    if(run>=64 && run<rest && count+run+2<=240){
     unsigned tail=span_piece(b+at+count+run,rest-run);
     if(tail<=2)count+=run+tail;
    }
   }
  }
  bool ok=count>240?"""
            s = once(s, old, new)
        (out / name).write_text(s, newline="\n")

    if mode in ("fixed", "fixed_retire"):
        name = "nes_native_sink165.c"
        s = (base / name).read_text()
        # Compare two standard size DATA packets to the fine-grained
        # word-repeat format on a fully materialized two-row raw payload.
        s = once(s, "oldcost=wire_cost789(b,n,false),newcost=wire_cost789(b,n,true);",
                 "oldcost=wire_cost789(b,n,false),newcost=(section==5 && offset==1121 && n==384)?oldcost:wire_cost789(b,n,true);")
        (out / name).write_text(s, newline="\n")

    if mode in ("owned", "owned_ready"):
        # Only an already CRC-checked next END can use the shortened handoff.
        # Keep the public, conservative one-argument entry for existing callers.
        name = "nes_plan_service200.c"
        s = (base / name).read_text()
        s = once(s, "if(flags&2){p->finished=true;return true;}",
                 "if(flags&2){if(flags!=2)return fail(p,4);p->finished=true;return true;}")
        s = once(s, "bool nes_plan200_retire(struct nes_plan200 *p){",
                 "bool nes_plan200_handoff790(struct nes_plan200 *p,bool complete){")
        s = once(s, "  if(!read509(p,rx,phase))return false;\n  if(rx[3]&0xf8)",
                 "  unsigned accepted=0;\n  if(!complete || sent){\n  if(!read509(p,rx,phase))return false;\n  if(rx[3]&0xf8)")
        s = once(s, "  unsigned accepted=(unsigned)rx[4]*256+rx[5];\n  if(!sent){",
                 "  accepted=(unsigned)rx[4]*256+rx[5];\n  }\n  if(!sent){")
        s = once(s, "if(rx[3]!=2||accepted!=p->sent)", "if(!complete && (rx[3]!=2||accepted!=p->sent))")
        s += "\nbool nes_plan200_retire(struct nes_plan200 *p){return nes_plan200_handoff790(p,false);}\n"
        (out / name).write_text(s, newline="\n")
        name = "nes_plan_service200.h"
        s = (base / name).read_text().replace("bool nes_plan200_retire(", "bool nes_plan200_handoff790(struct nes_plan200 *,bool);\nbool nes_plan200_retire(")
        (out / name).write_text(s, newline="\n")
        name = "nes_native_runtime165.c"
        runtime = out / name if mode=="owned_ready" else base / name
        s = once(runtime.read_text(),"nes_plan200_retire(&s->plan)",
                 "nes_plan200_handoff790(&s->plan,r->state==NES_NATIVE165_COMPLETE && r->ready183)")
        (out / name).write_text(s, newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("mode", choices=("retire","ready","both","raw_bridge","bridge_retire","raw_planes","fixed","fixed_retire","owned","owned_ready"))
    a = parser.parse_args()
    prepare(a.base, a.out, a.mode)
