"""Warm inactive-bank preupload of independently received compact raw rows."""
import json
from unittest.mock import patch
from build_nes_trace_replay import Code
from nes_admission838 import CLIENT as PARENT
from nes_window837 import ORIGIN, PROBES, codec, pack

CLIENT=PROBES/"nes-section841/client-relatch"
SCOPED=CLIENT.parent/"client-checked-stop"
PENDING,DONE,WORDS,VALID,BIT=0x1504,0x1506,0x1508,0x1512,0x1514


def build(scoped=False):
    dest=SCOPED if scoped else CLIENT
    body=bytearray((PARENT/"body.bin").read_bytes())
    old=json.loads((PARENT/"labels.json").read_bytes())
    c=Code(ORIGIN+len(body));c.labels.update(old)
    def hook(name,op,encoded):
        i=old[name]-ORIGIN
        before=bytes.fromhex(encoded)
        assert body[i:i+len(before)]==before
        c.label(name+"841")
        body[i:i+len(before)]=bytes([op])+(c.labels[name+"841"]&65535).to_bytes(2,"little")+bytes([0xea])*(len(before)-3)
    def imm(v):
        c.emit(0xa9);c.word(v)
    def lda(v):c.absolute(0xad,v)
    def sta(v):c.absolute(0x8d,v)
    def jcc(op,label):
        c.emit(op^0x20,3);c.jump(label)
    def lut(name):
        c.long(0xbf,ORIGIN);c.jumps.append((len(c.data)-3,name))

    if scoped:
        # Only a new transaction or a section 5 admission can change these
        # bytes. The original SEAL still validates identity, extents,
        # display semantics and coverage. Fault and STOP expire the proof.
        hook("accept838",0x20,"9c0215")
        lda(0x1200);c.emit(0x29,255,0,0xc9,1,0);c.branch(0xf0,"expire841")
        lda(0x1200);c.emit(0x29,0,255,0xc9,0,5);c.branch(0xd0,"keep841")
        c.label("expire841");c.absolute(0x9c,0x1502)
        c.label("keep841");c.emit(0x60)
    for name,orig in (("begin","9cd814"),("invalidate838","9c0215")):
        hook(name,0x20,orig)
        for v in (PENDING,DONE,VALID):c.absolute(0x9c,v)
        c.emit(*bytes.fromhex(orig),0x60)
    hook("expand833",0x4c,"c2206460")
    c.emit(0xc2,0x20,0xa2,8,0)
    c.label("save841");c.long(0xbf,0x400010);c.absolute(0x9d,WORDS);c.emit(0xca,0xca);c.branch(0x10,"save841")
    imm(1);sta(VALID);c.emit(0x64,0x60);c.absolute(0x4c,(old["expand833"]+4)&65535)
    hook("record838",0x20,"ee0215")
    c.absolute(0xee,0x1502)
    lda(VALID);c.branch(0xf0,"unarmed841")
    lda(0x1250);c.branch(0xd0,"unarmed841")
    lda(0x1034);c.absolute(0xcd,0x1032);c.branch(0xf0,"unarmed841")
    c.emit(0xaa,0xe2,0x20);c.absolute(0xbd,0x125a);c.emit(0xc9,2,0xc2,0x20);c.branch(0xd0,"unarmed841")
    # Match only acknowledged physical rows on this bank. A zero record
    # cannot attest a uniform byte. All other rows need a real write.
    imm(0);c.absolute(0xae,0x1034);c.branch(0xf0,"bank0841")
    c.emit(0xa0,22,0);c.branch(0x80,"mask841")
    c.label("bank0841");c.emit(0xa0,10,0)
    c.label("mask841");c.emit(0xa2,10,0);sta(PENDING)
    c.label("bits841");c.absolute(0xbd,0x14a0);c.branch(0xf0,"dirty841")
    c.absolute(0xd9,0x14ac);c.branch(0xd0,"dirty841");c.emit(0x18);c.branch(0x80,"shift841")
    c.label("dirty841");c.emit(0x38)
    c.label("shift841");c.absolute(0x2e,PENDING);c.emit(0x88,0x88,0xca,0xca);c.branch(0x10,"bits841")
    c.label("unarmed841");c.emit(0x60)

    hook("prefix523",0x4c,"ad2410")
    lda(PENDING);c.branch(0xd0,"pending841")
    c.label("original841");lda(0x1024);c.absolute(0x4c,(old["prefix523"]+3)&65535)
    c.label("pending841")
    c.emit(0xe2,0x20);lda(0x4212);c.branch(0x10,"normal841")
    lda(0x213f);lda(0x213f);c.emit(0x89,0x40);c.branch(0xd0,"normal841")
    lda(0x2137);lda(0x213f);c.emit(0x89,0x40);c.branch(0xf0,"normal841")
    lda(0x213d);c.emit(0xeb);lda(0x213d);c.emit(0x29,1);c.branch(0xd0,"normal841")
    c.emit(0xeb,0xc9,225);c.branch(0x90,"normal841");c.emit(0xc9,246);c.branch(0x90,"grant841")
    c.label("normal841");c.emit(0xc2,0x20);c.jump("original841")
    c.label("grant841");lda(0x6001);c.branch(0x10,"queue841")
    c.store(0x1236,1);c.emit(0xc2,0x20);c.jump("cancel841")
    c.label("queue841");lda(0x6000);c.emit(0x29,1);c.branch(0xd0,"normal841")
    c.emit(0xc2,0x20,0xa2,0,0);lda(PENDING)
    c.label("pick841");c.emit(0x4a);c.branch(0xb0,"selected841");c.emit(0xe8,0xe8);c.branch(0x80,"pick841")
    c.label("selected841");lut("bit841");sta(BIT)
    # Invalidate the target's old value before physical mutation. Implicit
    # planes remain valid. STOP/BEGIN clears speculative completions.
    c.emit(0x8a);c.absolute(0xac,0x1034);c.branch(0xf0,"slot841");c.emit(0x18,0x69,12,0)
    c.label("slot841");c.emit(0xa8);imm(0);c.absolute(0x99,0x14ac)
    lut("src841");c.emit(0x18);c.absolute(0x6d,0x1020);sta(0x4302)
    lut("dst841");c.absolute(0xac,0x1034);c.branch(0xf0,"dest841");c.emit(0x18,0x69,0,0x20)
    c.label("dest841");sta(0x2116)
    # The op9 packet contains five words for six rows (first pair shared).
    # Check each physical source word again before starting this DMA.
    c.emit(0xe0,0,0);c.branch(0xf0,"word841");c.emit(0xca,0xca)
    c.label("word841");c.absolute(0xbd,WORDS);c.absolute(0xae,0x4302);c.emit(0xa0,32,0)
    c.label("check841");c.long(0xdf,0x7f0000);jcc(0xd0,"defer841");c.emit(0xe8,0xe8,0x88);c.branch(0xd0,"check841")
    imm(0x1801);sta(0x4300);imm(0x7f);sta(0x4304);imm(64);sta(0x4305)
    c.emit(0xe2,0x20)
    # The 32 source-word checks may span several scanlines. Relatch at
    # the actual grant, then arbitrate STOP and head immediately before DMA.
    lda(0x4212);c.branch(0x10,"normal_end841")
    lda(0x213f);lda(0x213f);c.emit(0x89,0x40);c.branch(0xd0,"normal_end841")
    lda(0x2137);lda(0x213f);c.emit(0x89,0x40);c.branch(0xf0,"normal_end841")
    lda(0x213d);c.emit(0xeb);lda(0x213d);c.emit(0x29,1);c.branch(0xd0,"normal_end841")
    c.emit(0xeb,0xc9,225);c.branch(0x90,"normal_end841");c.emit(0xc9,245);c.branch(0xb0,"normal_end841")
    lda(0x6001);c.branch(0x30,"stop841");lda(0x6000);c.emit(0x29,1);c.branch(0xd0,"normal_end841")
    c.store(0x2115,0x81);c.label("dma841");c.store(0x420b,1);c.store(0x2115,0x80);c.emit(0xc2,0x20)
    lda(BIT);c.absolute(0x0c,DONE);c.absolute(0x1c,PENDING)
    c.label("complete841");lda(PENDING);c.branch(0xf0,"finished841");c.jump("pending841")
    c.label("finished841");c.jump("skip523")
    c.label("stop841");c.store(0x1236,1);c.emit(0xc2,0x20);c.jump("cancel841")
    c.label("normal_end841");c.emit(0xc2,0x20);c.jump("original841")
    # A changed WRAM word must cancel the transaction even if the sealed
    # fallback would otherwise transmit that row later.
    c.label("defer841");imm(1);sta(0x1236)
    c.label("cancel841");c.absolute(0x9c,0x125a)
    c.absolute(0x20,old["invalidate635"]&65535);c.jump("stop523")
    for name,values in (("bit841",[1<<i for i in range(6)]),("src841",[0x6961+64*i for i in range(6)]),
                        ("dst841",[0x2800+8*(i//2)+i%2 for i in range(6)])):
        c.label(name)
        for v in values:c.word(v)
    hook("raw_dma489",0x4c,"a478c01500")
    c.emit(0x48);lda(0x125c);c.emit(0x3a);c.branch(0xd0,"legacy841")
    lda(DONE);c.emit(0x05,0x78,0x85,0x78,0xc9,63,0);c.branch(0xd0,"legacy841")
    c.emit(0x68,0x64,0x78);c.jump("raw_return489")
    c.label("legacy841");c.emit(0x68,0xa4,0x78,0xc0,0x15,0);c.absolute(0x4c,(old["raw_dma489"]+5)&65535)
    body.extend(c.finish())
    used=260+len(pack(bytes(body),0))
    with patch.object(codec,"pack",pack),patch.object(codec,"STORED",max(5056,used)):
        codec.build(PROBES/"nes-reuse635/client04",dest,edit_body=lambda *_:bytes(body),
                    allow_extension=True,body_limit=8192,prefix_sizes=[0],medium_pages=True,
                    short_errors=True,boot_bytes=260,fast_backrefs=True)
    (dest/"labels.json").write_text(json.dumps(c.labels,indent=2))
    meta=json.loads((dest/"build.json").read_bytes());meta.update(program_bytes=used+64)
    (dest/"build.json").write_text(json.dumps(meta,indent=2))


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--scoped",action="store_true")
    build(parser.parse_args().scoped)
