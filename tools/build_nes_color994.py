"""Fill a checked four-byte repeat using fixed-source DMA plus sparse WRAM stores."""
from unittest.mock import patch
import json
import boot_nes_column854 as boot
from nes_blank959 import ORIGIN, LOADER_SOURCE
from build_nes_trace_replay import Code
from nes_color994 import PACKED, ROOT


def build(mode):
    labels=json.loads((PACKED/"labels.json").read_bytes())
    body=bytearray((PACKED/"body.bin").read_bytes())
    c=Code(ORIGIN+len(body));c.labels.update(labels)
    def imm(op,value):
        c.emit(op);c.word(value)
    def hook(pc,signature,target):
        off=pc-ORIGIN
        assert body[off:off+len(signature)]==signature
        body[off:off+3]=bytes([0x4c])+(c.labels[target]&65535).to_bytes(2,"little")
    # After section 4, span, cursor, identity and mark212 have all succeeded.
    # Match [a,b,a,a]. The incoming 4 bytes remain owned for the whole copy.
    if mode in ("scatter3","both3"):
        pc=labels["literal1814"]
        c.label("repeat994");c.emit(0xc2,0x20)
        c.absolute(0xad,0x1200);imm(0xc9,0x0408);c.branch(0xd0,"literal994")
        c.emit(0xe2,0x20);c.long(0xaf,0x400010);c.long(0xcf,0x400012);c.branch(0xd0,"literal8_994")
        c.long(0xcf,0x400013);c.branch(0xf0,"fill994")
        c.label("literal8_994");c.emit(0xc2,0x20)
        c.label("literal994");imm(0xa9,0x8000);c.absolute(0x4c,(pc+5)&65535)
        c.label("fill994");c.emit(0xc2,0x20);imm(0xa9,0x8008);c.absolute(0x8d,0x4300)
        imm(0xa9,16);c.absolute(0x8d,0x4302);c.emit(0xe2,0x20);c.store(0x4304,0x40);c.emit(0xc2,0x20)
        c.absolute(0xad,0x120c);c.emit(0x85,0x60,0xa6,0x7a)
        c.absolute(0x20,labels["service"]&65535);c.branch(0xf0,"chunk994");c.jump("stop_packet")
        c.label("chunk994");c.emit(0xa5,0x60);imm(0xc9,65);c.branch(0x90,"count994");imm(0xa9,64)
        c.label("count994");c.absolute(0x8d,0x4305);c.emit(0xa8,0x49,0xff,0xff,0x38,0x65,0x60,0x85,0x60)
        c.emit(0xe2,0x20);c.store(0x420b,1);c.long(0xaf,0x400011)
        imm(0xc0,64);c.branch(0xd0,"short994")
        for i in range(1,64,4):c.long(0x9f,0x7f0000+i)
        c.emit(0xc2,0x20,0x8a,0x18);imm(0x69,64);c.emit(0xaa);c.branch(0x80,"poll994")
        c.label("short994");c.long(0x9f,0x7f0001)
        c.emit(0xe8,0xe8,0xe8,0xe8,0x88,0x88,0x88,0x88);c.branch(0xd0,"short994");c.emit(0xc2,0x20)
        c.label("poll994");c.absolute(0x20,labels["service"]&65535);c.branch(0xf0,"next994");c.jump("stop_packet")
        c.label("next994");c.emit(0xa5,0x60);c.branch(0xf0,"ok994");c.jump("chunk994")
        c.label("ok994");c.jump("accepted")
        hook(pc,bytes.fromhex("c220a90080"),"repeat994")
    if mode in ("uniform3","both3"):
        # The existing uniform fill normally handles large palette ranges.
        # Use the same checked source and bounded 64B DMA for small OAM words.
        pc=labels["repeated1815"]
        c.label("word994");c.absolute(0xad,0x1201);c.emit(0xc9,4);c.branch(0xd0,"original994")
        c.long(0xaf,0x400010);c.long(0xcf,0x400011);c.branch(0xd0,"oldword994")
        c.emit(0xc2,0x20);c.absolute(0xad,0x120c);c.absolute(0x4c,(labels["generic548"]+10)&65535)
        site=labels["generic548"]-ORIGIN+10
        assert body[site:site+2]==bytes.fromhex("8560")
        c.label("oldword994");c.jump("word516")
        c.label("original994");c.absolute(0x4c,(pc+3)&65535)
        hook(pc,bytes.fromhex("ad0112c903"),"word994")
        # Existing fill completion has a section-5 bookkeeping path. Route
        # OAM directly to accepted, exactly like the generic word loop.
        pc=body.index(bytes.fromhex("ad011229ff00c90300d003"),labels["zero_chunk516"]-ORIGIN)+ORIGIN
        c.label("fill_done994");c.absolute(0xad,0x1201);imm(0x29,255);imm(0xc9,4)
        c.branch(0xd0,"old_done994");c.jump("accepted")
        c.label("old_done994");c.absolute(0x4c,(pc+6)&65535)
        hook(pc,bytes.fromhex("ad011229ff00"),"fill_done994")
    body.extend(c.finish())
    with patch.object(boot,"STORED",5800):
        boot.build(LOADER_SOURCE,ROOT/mode,bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


if __name__=="__main__":
    for m in ("scatter3","uniform3","both3"):build(m)
