"""Charge descriptor bytes on admission and retire only synchronous pre-SEAL DMA."""
import argparse
import json
from unittest.mock import patch

from build_nes_trace_replay import Code
from nes_group835 import OUT as BASE, PROBES
from prepare_nes_map828 import codec, pack

OUT = PROBES / "nes-charge836"
ORIGIN = 0x7e2000
LIVE = 0x1500


def build(mode):
    src = BASE/"client-warm"
    body = bytearray((src/"body.bin").read_bytes())
    c = Code(ORIGIN+len(body))
    c.labels.update(json.loads((src/"labels.json").read_bytes()))

    def install(pc, expected, code):
        i=pc-ORIGIN
        assert body[i:i+len(expected)]==expected
        body[i:i+len(code)]=code

    def call_at(pc, old, name):
        c.label(name)
        install(pc,bytes.fromhex(old),bytes([0x20])+(c.labels[name]&65535).to_bytes(2,"little"))

    if mode in ("charge","both","bank"):
        call_at(c.labels["valid_a212"]+3,"9c5012","clear836")
        c.absolute(0x9c,LIVE);c.absolute(0x9c,0x1250);c.emit(0x60)
        # The independent coverage bitmap forbids a second charge for any
        # BG/OBJ/map unit. Even a full bank plus the one raw job fits 16 bits.
        # Both new descriptors and successful extensions contribute $74 bytes.
        call_at(c.labels["append212"],"ad5012","append836")
        c.emit(0xa5,0x74,0x18);c.absolute(0x6d,LIVE);c.absolute(0x8d,LIVE)
        c.absolute(0xad,0x1250);c.emit(0x60)
        # Y is the actual DAS just selected. This point is reached after
        # STOP/queue arbitration, immediately before synchronous MDMAEN.
        call_at(c.labels["dma_start680"]+2,"ad0243","retire836")
        c.emit(0x98,0x49,255,255,0x38);c.absolute(0x6d,LIVE);c.absolute(0x8d,LIVE)
        c.absolute(0xad,0x4302);c.emit(0x60)
        # The prior guard allows at most nine entries. Charging all nine
        # setup margins is conservative even for a partly consumed group.
        at=body.index(bytes.fromhex("a9200a8d56124c942b"),c.labels["borrow835"]-ORIGIN)
        # Fresh groups need no special tag once the borrowed group bypasses
        # budget538. Reuse the obsolete reset and dispatch functions in situ.
        orig=(PROBES/"nes-tail834/client-inspect/body.bin").read_bytes()
        for label in ("fresh618","group_ready538"):
            i=c.labels[label]-ORIGIN
            body[i:i+3]=orig[i:i+3]
        start=c.labels["reset835"]
        block=Code(start);block.labels.update(c.labels);block.label("charge836")
        block.absolute(0xad,LIVE);block.emit(0xc9);block.word(1729)
        block.branch(0xb0,"single835");block.absolute(0xae,0x1250);block.branch(0x80,"early835")
        end=c.labels["early835"]-start
        seq=block.finish();assert len(seq)<=end
        body[start-ORIGIN:start-ORIGIN+end]=seq+bytes(end-len(seq))
        c.labels["charge836"]=start
        displacement=start-ORIGIN-at-2
        assert -128<=displacement<=127
        install(ORIGIN+at,bytes.fromhex("a9200a8d56124c942b"),bytes([0x80,displacement&255])+bytes(7))
    if mode in ("raw","both","bank"):
        # Three warm receipt patterns share a loop over physical source and
        # destination offsets. Each actual DMA still begins with service().
        r=Code(c.labels["pairs624"]);r.labels.update(c.labels)
        r.branch(0xf0,"mask15_836");r.emit(0xc0,0x1d,0);r.branch(0xf0,"mask1d_836")
        r.emit(0xc0,0x2c,0);r.branch(0xf0,"mask2c_836");r.jump("generic624")
        r.label("mask15_836");r.emit(0xa2,0,0);r.branch(0x80,"three836")
        r.label("mask1d_836");r.emit(0xa2,6,0,0xa0,2,0);r.branch(0x80,"raw836")
        r.label("mask2c_836");r.emit(0xa2,10,0)
        r.label("three836");r.emit(0xa0,3,0)
        r.label("raw836");r.emit(0x4a,0x85,0x76)
        # Both fresh and borrowed SEAL group entries have programmed these
        # static channel registers. No preceding ordinary VRAM DMA alters them.
        if mode!="bank":
            r.emit(0xa9,1,0x18);r.absolute(0x8d,0x4300);r.emit(0xa9,0x7f,0);r.absolute(0x8d,0x4304)
        r.emit(0xe2,0x20);r.store(0x2115,0x81);r.emit(0xc2,0x20)
        r.label("row836");r.absolute(0x20,c.labels["service"]&65535);r.branch(0xf0,"send836");r.jump("raw_stop489")
        def table(label):
            r.long(0xbf,ORIGIN);r.jumps.append((len(r.data)-3,label))
        r.label("send836");table("src836")
        r.emit(0x18);r.absolute(0x6d,0x1020);r.absolute(0x8d,0x4302)
        table("dst836")
        r.emit(0x05,0x76);r.absolute(0x8d,0x2116)
        r.emit(0xa9,64,0);r.absolute(0x8d,0x4305);r.emit(0xe2,0x20);r.store(0x420b,1);r.emit(0xc2,0x20,0xe8,0xe8)
        r.emit(0x88);r.branch(0xd0,"row836")
        r.emit(0x64,0x78);r.jump("raw_return489")
        rows=(1,3,5,1,5,0,1,4)
        r.label("src836")
        for row in rows:r.word(0x6961+64*row)
        r.label("dst836")
        for row in rows:r.word(8*(row//2)+row%2)
        raw=r.finish()
        start=r.labels["pairs624"]-ORIGIN
        space=r.labels["raw_boot489"]-r.labels["pairs624"]
        assert len(raw)<=space,(len(raw),space)
        body[start:start+space]=raw+bytes(space-len(raw))
        c.labels.update(r.labels)
    if mode=="bank":
        # prepare665 now owns the fresh wait, continuation835 owns the
        # loop edge. These fall-through bytes follow unconditional jumps.
        at=c.labels["group_ready538"]-ORIGIN+3
        install(ORIGIN+at,bytes.fromhex("20682d9070"),bytes(5))
        at=body.index(bytes.fromhex("90b74c0c2b"),c.labels["transfer212"]-ORIGIN)
        assert body[at-3:at]==bytes([0x4c])+(c.labels["continuation835"]&65535).to_bytes(2,"little")
        install(ORIGIN+at,bytes.fromhex("90b74c0c2b"),bytes(5))
        # DBR 7F shortens the actual eight comparisons in the inner loop.
        # Restore the caller's DBR on both exits before WRAM repair or ACK.
        start=c.labels["inspect834"]
        end=c.labels["repair834"]
        r=Code(start);r.labels.update(c.labels)
        r.emit(0x8b,0xf4,0x7f,0x7f,0xab,0xab)
        r.label("read836")
        for pos in range(0,16,2):
            r.absolute(0xdd,pos);r.branch(0xd0,"repair836")
        r.emit(0x8a,0x18,0x69,16,0,0xaa,0xa5,0x62,0x88)
        r.branch(0xd0,"read836");r.emit(0xab);r.jump("verified834")
        r.label("repair836");r.emit(0xab)
        seq=r.finish()
        assert len(seq)<=end-start
        body[start-ORIGIN:end-ORIGIN]=seq+bytes([0xea])*(end-start-len(seq))
        c.labels.update(r.labels)
    body.extend(c.finish())
    out=OUT/("final-"+mode)
    with patch.object(codec,"pack",pack):
        codec.build(PROBES/"nes-reuse635/client04",out,edit_body=lambda *_:bytes(body),
                    allow_extension=True,prefix_sizes=[2],medium_pages=True,short_errors=True,
                    boot_bytes=280,fast_backrefs=True,single_word_prefix=True)
    (out/"labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=("charge","raw","both","bank"))
    build(parser.parse_args().mode)
