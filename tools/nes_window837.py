"""Bound the palette wait and retain STOP arbitration between sealed DMA jobs."""
import argparse
import json
from unittest.mock import patch

from build_nes_trace_replay import Code
from nes_charge836 import ORIGIN, PROBES, OUT as LAST
from nes_raw506 import once
from prepare_nes_map828 import codec, pack

OUT = PROBES / "nes-window837"
BASE = PROBES / "nes-output823/link-836split"


def palette(mode):
    src = BASE / "src/nes_native_sink165.c"
    text = src.read_text()
    span = " if(!span(s,3,0,p->cgram,512))return false;"
    at = " if(!p->scroll_issued && !p->map_dirty && s->plan && s->plan->window"
    # CGRAM is immutable here. Its own ordinary sends still service a ready
    # bulk and use normal queue credit. The wait now precedes OAM.
    text = once(once(text,span+"\n",""),at,span+"\n"+at)
    if mode=="seal":
        start=text.index(at)
        end=text.index(" if(!oam227",start)
        # Finish the ordinary writes first. A displayed-history command
        # remains on its original gate; it already binds both sections.
        wait=text[start:end]
        text=text[:start]+text[end:]
        wait=once(wait," if(!p->scroll_issued", " if(!same && !p->scroll_issued")
        anchor=" uint8_t descriptor[168];"
        text=once(text,anchor,wait+anchor)
    if mode=="shared":
        # Both paths are at BG completion, after map527 has drained.
        # A pending bulk keeps ownership. Stale pages use normal arbitration.
        guard="s->plan->started && !s->plan->ending && !s->plan->sent && p->map_dirty"
        text=once(text,guard,"(!p->map_dirty || (s->plan->started && !s->plan->ending && !s->plan->sent))")
        text=once(text,"if(!packet(s,24,5,0,p->hdma,n) || !packet_wire(s,25,5,n,zero,2,1121-n))",
                  "if(!packet(s,p->map_dirty?24:2,5,0,p->hdma,n) || !packet_wire(s,p->map_dirty?25:5,5,n,zero,2,1121-n))")
        text=once(text,at," if(!p->map_dirty && s->plan && s->plan->window")
    if mode=="prefix":
        # A stale, fully produced map has the same validated HDMA prefix.
        # Use normal progress/credit on both sends; retain the 704B map
        # progress check before OAM even when the prefix was issued early.
        anchor="  if(fragments>112/4){"
        text=once(text,anchor,"""  if(fragments>112/4 && !p->map_dirty && !p->scroll_issued &&
     !(uint32_t)map && !s->plan->bulk_pending){
   if(!(n&1))p->hdma[n++]=0;
   if(!packet(s,2,5,0,p->hdma,n) || !packet_wire(s,5,5,n,zero,2,1121-n))return false;
   p->scroll_issued=true;
   return true;
  }
"""+anchor)
        text=once(text,at," if(!p->map_dirty && s->plan && s->plan->window")
    dst = OUT / ("patch-"+mode)
    dst.mkdir(exist_ok=True,parents=True)
    (dst/src.name).write_text(text,newline="\n")


def receiver():
    src = LAST / "final-bank"
    body = bytearray((src/"body.bin").read_bytes())
    labels = json.loads((src/"labels.json").read_bytes())
    start = labels["continuation835"]
    end = labels["clear836"]
    # A just-finished, sealed DMA owns the channel. X is the committed next
    # descriptor. Under VBlank service only clears the joypad sample latch.
    # Route an observed STOP directly into the original invalidation path.
    # Outside VBlank run the full service (including the controller read).
    c = Code(start)
    c.labels.update(labels)
    c.absolute(0xec,0x103a)
    c.branch(0x90,"test837")
    c.jump("group538")
    c.label("test837")
    c.emit(0xe2,0x20)
    c.absolute(0xad,0x6001);c.branch(0x30,"seen837")
    c.absolute(0xad,0x4212);c.branch(0x10,"slow837")
    c.absolute(0x9c,0x1238)
    c.emit(0xc2,0x20);c.jump("upload_loop212")
    c.label("slow837")
    c.emit(0xc2,0x20);c.absolute(0x20,labels["service"]&65535)
    c.branch(0xf0,"resume837");c.jump("cancel169")
    c.label("resume837");c.jump("upload_loop212")
    # Enter service's observed-STOP arm with its original PHP/return
    # stack shape. Even a one-read STOP invalidates both bank histories.
    c.label("seen837");c.emit(0xf4);c.word((labels["cancel169"]-1)&65535)
    c.emit(0x08)
    stop=labels["service"]+10
    assert body[stop-ORIGIN:stop-ORIGIN+5]==bytes.fromhex("a9018d3612")
    c.absolute(0x4c,stop&65535)
    # Move the three admission accounting subroutines after the new loop.
    moved = body[end-ORIGIN:]
    for name in ("clear836","append836","retire836"):
        old=labels[name]
        addr=start+len(c.data)+old-end
        call=bytes([0x20])+(old&65535).to_bytes(2,"little")
        site=bytes(body).index(call)
        assert body.count(call)==1
        body[site+1:site+3]=(addr&65535).to_bytes(2,"little")
        c.labels[name]=addr
    body[start-ORIGIN:]=c.finish()+moved
    dst=OUT/"client-sticky"
    with patch.object(codec,"pack",pack):
        codec.build(PROBES/"nes-reuse635/client04",dst,edit_body=lambda *_:bytes(body),
                    allow_extension=True,prefix_sizes=[0],medium_pages=True,short_errors=True,
                    boot_bytes=260,fast_backrefs=True)
    (dst/"labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=("client-sticky","palette","prefix","shared","seal"))
    action=parser.parse_args().action
    if action.startswith("client"):
        receiver()
    else:
        palette(action)
