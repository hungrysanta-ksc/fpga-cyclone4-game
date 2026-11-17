"""MMC826 self-contained map rows. Opcode 9 section 2 carries 18 literal bytes per 64B row."""
from pathlib import Path
import json
from unittest.mock import patch

from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import once, sha
from nes_report828 import reports
from prepare_nes_longrun694 import codec
from pack_nes_static751 import pack

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / "probes"
OUT = PROBES / "nes-map828"


def sender(right_only=False):
    arm = PROBES / "nes-output823/link-826/src"
    target = OUT / ("patch-right" if right_only else "patch")
    target.mkdir(parents=True, exist_ok=True)
    name = "nes_native_sink165.c"
    text = (arm / name).read_text()
    mark = " put16(b+12,n);if(n){"
    text = once(text, mark, """
 /* Keep the denser repeated-word encoding. The right page is independently
  * reconstructible only when every omitted byte in every row is zero. */
 if(b[0]==2 && section==2 && at>=2048 && n && !(n&63)){
  unsigned pos=0;
  while(pos<n && !data[pos+18] && !memcmp(data+pos+18,data+pos+19,45))pos+=64;
  if(pos==n){
   unsigned packed=0;
   for(pos=0;pos<n;pos+=64){
    memcpy(b+16+packed,data+pos,18);
    packed+=18;
   }
   b[0]=9;n=packed;
  }
 }
 put16(b+12,n);if(n && !(b[0]==9 && section==2)){""")
    text = once(text, "s->plan->window->last[0]==2 &&", "(s->plan->window->last[0]==2 || s->plan->window->last[0]==9) &&")
    if right_only:
        # A cold refresh or mixed left/right transition retains the original
        # wire format. This decision uses only the current complete dirty mask.
        text = once(text," if(s->plan && op>=2",
            " bool packed_right=(op==26 || op==27);\n"
            " if(packed_right)op=(op==26?24:2);\n if(s->plan && op>=2")
        text = once(text,"if(b[0]==2 && section==2 && at>=2048","if(packed_right && b[0]==2")
        old = "if(!packet(s,(early==1||early==3||adjacent)?24:2,2,first*64,"
        text = once(text,old,
            "bool granted=early==1||early==3||adjacent;\n"
            "  unsigned command=(uint32_t)mask?(granted?24:2):(granted?26:27);\n"
            "  if(!packet(s,command,2,first*64,")
    (target / name).write_text(text)
    reports(arm,target)


def client(fast=True):
    parent = PROBES / "nes-output815/client"
    assert sha(parent/"sink165.sfc") == "3ca9aaefd9efad64a3cb63b59b627314f9f6b8e87fb79e236ba7e7d01fa856e1"
    body = bytearray((parent/"body.bin").read_bytes())
    labels = json.loads((parent/"labels.json").read_bytes())
    c = Code(0x7e2000+len(body))
    c.labels.update(labels)
    def gate(address, old, label):
        pos = address-0x2000
        assert body[pos:pos+3] == bytes.fromhex(old)
        body[pos:pos+3] = b'\x4c'+(c.labels[label]&65535).to_bytes(2,'little')
    c.label("header828")
    c.absolute(0xad,0x1200)
    c.emit(0xc9,9,2)
    c.branch(0xf0,"rows828")
    c.jump("reuse635")
    c.label("rows828")
    c.absolute(0xad,0x120e)
    c.branch(0xd0,"reject828")
    c.absolute(0xad,0x120c)
    # Verify actual transport extent (already checked against queue length)
    # before common data bounds, 64B alignment and independent receipt bitmap.
    for wire,span in ((18,64),(36,128),(54,192)):
        c.emit(0xc9,wire,0)
        c.branch(0xd0,f"next828_{wire}")
        c.emit(0xa9,span,0)
        c.absolute(0x8d,0x120c)
        c.jump("data")
        c.label(f"next828_{wire}")
    c.label("reject828");c.jump("bad_packet")
    gate(0x224c,"4c d4 34","header828")

    c.label("literal828")
    # This dispatch receives an 8-bit opcode. All ordinary DATA/BULK packets
    # and OAM reuse use the original literal DMA. X is the section word offset.
    c.emit(0xc9,9);c.branch(0xd0,"literal_original828")
    c.emit(0xe0,4,0);c.branch(0xf0,"restore828")
    c.label("literal_original828");c.jump("literal1814")
    gate(0x252f,"4c db 25","literal828")
    c.label("restore828")
    if fast:
        # MVN writes the literal prefix directly. Its DBR result selects WRAM
        # for the fixed-offset word stores and independent readback below.
        c.emit(0xc2,0x20,0xa2,16,0,0xa4,0x7a)
        c.absolute(0xad,0x120c)
        c.label("row828")
        c.emit(0x48,0x8b,0xda,0x5a,0xa9,17,0,0x54,0x7f,0x40)
        c.emit(0xa9,0,0)
        for opcode,label in ((0x99,"fill_tail828"),(0x19,"check_tail828")):
            c.emit(0x5a,0xa2,5,0)               # five groups of four words
            c.label(label)
            for off in (0,2,4,6):
                c.absolute(opcode,off)
            c.emit(*([0xc8]*8),0xca);c.branch(0xd0,label)
            for off in (0,2,4):
                c.absolute(opcode,off)
            c.emit(0x7a)
        c.emit(0x7a,0xfa)
        # Pull instructions set flags. Re-test the accumulated 23 words.
        c.emit(0xc9,0,0);c.branch(0xd0,"restore_bad828")
        c.label("check_prefix828");c.long(0xbf,0x400000);c.absolute(0xd9,0)
        c.branch(0xd0,"restore_bad828")
        c.emit(0xe8,0xe8,0xc8,0xc8,0x98,0x29,63,0,0xc9,18,0)
        c.branch(0xd0,"check_prefix828")
        c.emit(0x98,0x18,0x69,46,0,0xa8,0xab)
        call(c,"service");c.branch(0xf0,"continue828")
        c.emit(0x68);c.jump("stop_packet")
        c.label("restore_bad828");c.emit(0xab,0x68);c.jump("bad_packet")
        c.label("continue828");c.emit(0x68,0x38,0xe9,64,0)
        c.branch(0xf0,"done828");c.jump("row828")
        c.label("done828");c.jump("accepted")
    else:
        c.store(0x7c,0x7f)
        c.emit(0xc2,0x20,0xa2,0,0,0xa0,0,0)
        c.label("row828")
        # X is the packet cursor, Y the expanded offset. Write and then verify
        # WRAM from the independently addressed cartridge bytes / implicit zero.
        c.emit(0xda,0x5a)
        c.label("prefix828");c.long(0xbf,0x400010);c.emit(0x97,0x7a,0xe8,0xe8,0xc8,0xc8)
        c.emit(0x98,0x29,63,0,0xc9,18,0);c.branch(0xd0,"prefix828")
        c.label("tail828");c.emit(0xa9,0,0,0x97,0x7a,0xc8,0xc8,0x98,0x29,63,0)
        c.branch(0xd0,"tail828")
        c.emit(0x7a,0xfa)
        c.label("check_prefix828");c.long(0xbf,0x400010);c.emit(0xd7,0x7a)
        c.branch(0xd0,"reject828")
        c.emit(0xe8,0xe8,0xc8,0xc8,0x98,0x29,63,0,0xc9,18,0);c.branch(0xd0,"check_prefix828")
        c.label("check_tail828");c.emit(0xb7,0x7a);c.branch(0xd0,"reject828")
        c.emit(0xc8,0xc8,0x98,0x29,63,0);c.branch(0xd0,"check_tail828")
        call(c,"service");c.branch(0xf0,"continue828");c.jump("stop_packet")
        c.label("continue828");c.absolute(0xcc,0x120c);c.branch(0xd0,"row828");c.jump("accepted")
    body.extend(c.finish())
    out = OUT/("client-fast" if fast else "client-b")
    base = PROBES/"nes-reuse635/client04"
    with patch.object(codec,"pack",pack):
        codec.build(base,out,edit_body=lambda *_:bytes(body),allow_extension=True,
                    prefix_sizes=[256,128,64,16,2],medium_pages=True,boot_bytes=320,fast_backrefs=True)
    (out/"labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")


if __name__=="__main__":
    sender()
    sender(right_only=True)
    client(fast=False)
    client(fast=True)
