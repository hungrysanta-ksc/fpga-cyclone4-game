"""Give an inherited right-page map a bounded progress window after 768 bytes."""
from pathlib import Path
import argparse
import json
from unittest.mock import patch

from nes_raw506 import once
from nes_tail834 import PROBES
from link_nes_section832 import build
from build_nes_trace_replay import Code
from prepare_nes_map828 import codec, pack
from nes_repeat833 import client

OUT=PROBES/"nes-group835"
BASE=PROBES/"nes-output823/link-834bgdirty"


def receiver(extended=False):
    src=OUT/("warm-base" if extended else "client-inspect-compact")
    client(PROBES/"nes-seal831/client",src,
           expected="c9196b0a59c068e0100cbcc87eeaf1d424628c10c590115893352d404a118ca1",
           step=16,inspect_first=True,repair_step=4)
    dst=OUT/("client-warm" if extended else "client-group")
    body=bytearray((src/"body.bin").read_bytes())
    origin=0x7e2000
    c=Code(origin+len(body))
    c.labels.update(json.loads((src/"labels.json").read_bytes()))

    def hook(pc,expected,name,opcode=0x4c):
        i=pc-origin
        assert body[i:i+3]==bytes.fromhex(expected)
        c.label(name)
        body[i:i+3]=bytes([opcode])+(c.labels[name]&0xffff).to_bytes(2,"little")

    sample=c.labels["sample618"]
    i=body.index(bytes.fromhex("ad12421016ad0160"),sample-origin)
    hook(origin+i,"ad1242","sample835",0x20)
    c.emit(0xa0,0,0,0xc9,236);c.branch(0xb0,"sampled835");c.emit(0xc8)
    c.label("sampled835");c.absolute(0xad,0x4212);c.emit(0x60)
    i=body.index(bytes.fromhex("9c5612ad5212"),i)
    hook(origin+i,"9c5612","borrow835")
    c.emit(0xc0,1,0);c.branch(0xd0,"single835")
    # The compact verifier has already checked a warm form's row count.
    c.absolute(0xad,0x125c);c.emit(0x3a);c.branch(0xd0,"single835")
    if extended:
        # At most nine independently sealed descriptors remain. Raw is
        # charged at its full verified size even if only some rows changed.
        c.absolute(0xad,0x1250);c.emit(0x38);c.absolute(0xed,0x1252)
        c.emit(0xc9,73,0);c.branch(0xb0,"single835")
    else:
        c.absolute(0xad,0x1240);c.emit(0x3a);c.branch(0xd0,"single835")
    c.emit(0xa9);c.word(2592 if extended else 2240);c.absolute(0x8d,0x1256);c.jump("budget538")
    c.label("single835");c.absolute(0x9c,0x1256);c.absolute(0x4c,0x2000+i+3)
    hook(c.labels["fresh618"],"ae5212","reset835")
    c.emit(0xa0,0,0);c.absolute(0xae,0x1252);c.absolute(0x4c,(c.labels["fresh618"]+3)&65535)
    hook(c.labels["group_ready538"],"4c8036","ready835")
    c.emit(0xc0,1,0);c.branch(0xf0,"early835");c.jump("prepare665")
    c.label("early835");c.absolute(0x8e,0x103a);c.absolute(0x9c,0x1256);c.jump("one618")
    # Every continuation checks STOP before the next descriptor starts.
    i=body.index(bytes.fromhex("90b74c"),c.labels["transfer212"]-origin)
    hook(origin+i-3,"ec3a10","continuation835")
    c.absolute(0xec,0x103a);c.branch(0x90,"service835");c.jump("group538")
    c.label("service835");c.absolute(0x20,c.labels["service"]&65535)
    c.branch(0xf0,"continue835");c.jump("cancel169")
    c.label("continue835");c.jump("upload_loop212")
    body.extend(c.finish())
    with patch.object(codec,"pack",pack):
        codec.build(PROBES/"nes-reuse635/client04",dst,edit_body=lambda *_:bytes(body),
                    allow_extension=True,prefix_sizes=[128,64,16,2],medium_pages=True,boot_bytes=320,fast_backrefs=True)
    (dst/"labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")


def sender(mode):
    text=(BASE/"src/nes_native_sink165.c").read_text()
    anchor="  if(early==3){s->map_next=(uint8_t)g;continue;}"
    limit={"once":1,"progress":12}[mode]
    pause=f"""
  /* Four accepted packets cover the first 768 bytes of this stale page.
   * The consumer owns DMA. Status may already show a validated retirement;
   * wait for DMA progress only within a bounded number of guarded samples. */
  if(early==3 && !p->map_dirty && first==41 && count==3 &&
     (uint32_t)mask==0 && ((uint32_t)(mask>>32)&0x7fffffu)==0x7fffffu &&
     s->plan && !s->plan->bulk_pending && s->plan->window){{
   uint8_t ack[12];
   for(unsigned n=0;n<{limit};n++){{
    if(!nes_window184_drain(s->plan->window,ack))return fail(s,5);
    if(s->plan->window->status_flags&8)break;
   }}
  }}
"""
    dest=OUT/("patch-"+mode)
    dest.mkdir(exist_ok=True,parents=True)
    (dest/"nes_native_sink165.c").write_text(once(text,anchor,pause+anchor),newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("once","progress","client","warm"))
    p.add_argument("--overlay",action="store_true")
    a=p.parse_args()
    if a.mode in ("client","warm"):
        receiver(a.mode=="warm")
    elif a.overlay:
        build(a.mode,PROBES/("nes-output823/link-835"+a.mode),OUT,"nes_scroll810")
    else:
        sender(a.mode)
